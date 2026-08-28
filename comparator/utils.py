import re
import math
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_model_instance = None

def get_embedding_model():
    """
    Lazy-loads the Sentence-Transformers model to memory.
    Using a singleton pattern keeps subsequent request response times under 100ms.
    """
    global _model_instance
    import os
    # Render Free Tier RAM is strictly limited to 512MB. 
    # Bypassing PyTorch prevents the container from crash-looping due to Out Of Memory (OOM) SIGKILLs.
    if os.environ.get('RENDER_EXTERNAL_HOSTNAME') and not os.environ.get('ENABLE_TRANSFORMERS'):
        return None

    if _model_instance is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model_instance = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        except Exception:
            _model_instance = None
    return _model_instance


def extract_text_from_pdf(file_obj):
    """
    Extracts text content from a PDF file object.
    """
    text = ""
    try:
        reader = PdfReader(file_obj)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        text = f"Error reading PDF: {str(e)}"
    return text

def clean_text(text):
    """
    Cleans text by converting to lowercase, removing double spaces, and normalizing line endings.
    """
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_candidate_name(raw_text):
    """
    Heuristically extracts candidate name from the first few lines of the resume text.
    """
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    
    # Exclude lines that contain contact info, labels, or common resume titles
    exclude_keywords = [
        'resume', 'curriculum', 'vitae', 'contact', 'email', 'phone', 'mobile',
        'address', 'github', 'linkedin', 'profile', 'summary', 'experience', 'education'
    ]
    
    for line in lines[:5]:
        # Clean line to check keywords
        cleaned_line = line.lower()
        if any(kw in cleaned_line for kw in exclude_keywords):
            continue
        
        # Check if line looks like a name: 2 to 4 words, contains only letters/spaces, capitalized
        words = line.split()
        if 2 <= len(words) <= 4 and re.match(r'^[a-zA-Z\s\.\-\u00C0-\u017F]+$', line):
            return line
            
    return "Unknown Candidate"

def parse_years_of_experience(cleaned_text, raw_text):
    """
    Heuristically extracts years of experience from the resume.
    Looks for direct mentions of experience and sums up date ranges.
    """
    years = 0.0
    
    # Heuristic 1: Match direct mentions of years of experience
    # e.g., "5 years of experience", "3.5 yrs exp", "10+ years experience"
    exp_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)(?:\s+of)?\s*experience',
        r'experience\s*:\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)'
    ]
    
    direct_estimates = []
    for pattern in exp_patterns:
        matches = re.findall(pattern, cleaned_text)
        for m in matches:
            try:
                direct_estimates.append(float(m))
            except ValueError:
                pass
                
    if direct_estimates:
        # Take the maximum direct estimate
        years = max(direct_estimates)
        
    # Heuristic 2: Match date ranges (e.g. 2018 - 2021, Jan 2021 - Present)
    # Search in raw text line by line to maintain structure
    date_ranges = []
    # Match years in range like: 2018 - 2022, 2020 to Present, 12/2019 - 05/2021
    range_pattern = r'\b(19\d{2}|20\d{2})\b\s*(?:-|–|—|to)\s*\b(19\d{2}|20\d{2}|present|current|now)\b'
    
    for line in raw_text.split('\n'):
        matches = re.findall(range_pattern, line.lower())
        for start, end in matches:
            start_yr = int(start)
            if end in ['present', 'current', 'now']:
                # Assume current year is 2026 (based on current local time)
                end_yr = 2026
            else:
                end_yr = int(end)
                
            duration = end_yr - start_yr
            if 0 < duration <= 15: # Avoid anomaly ranges
                date_ranges.append(duration)
                
    if date_ranges:
        # Sum of non-overlapping is hard to calculate without full dates, so we can sum the durations
        # but cap the total to avoid duplicating parallel roles (e.g., student + freelancer)
        summed_ranges = sum(date_ranges)
        # We take the max of direct mentions and date ranges, capped at 30 years
        years = max(years, summed_ranges)
        
    return min(years, 30.0)

def extract_section(raw_text, section_keywords):
    """
    Attempts to extract a specific section from raw resume text based on header keywords.
    """
    lines = raw_text.split('\n')
    section_text = []
    in_section = False
    
    # Compile a regex to match headers
    # e.g., "Projects", "Work Experience", "Education"
    # Typically headers are short, on their own line, or capitalized
    header_pattern = re.compile(r'^\s*(?:[a-zA-Z\d\s\-\/&]+)\s*$')
    
    for line in lines:
        cleaned_line = line.strip()
        if not cleaned_line:
            continue
            
        # Detect if we are entering the target section
        if not in_section:
            # Check if any keyword matches the line
            if any(re.search(rf'\b{kw}\b', cleaned_line.lower()) for kw in section_keywords):
                # Ensure it looks like a header (not a sentence)
                if len(cleaned_line) < 40:
                    in_section = True
                    continue
        else:
            # Detect if we are leaving the section (another header starts)
            # If line is short, uppercase/capitalized, and matches other section keywords, stop
            other_sections = ['education', 'experience', 'skills', 'summary', 'certifications', 'languages', 'hobbies', 'contact']
            # Remove current section keywords from check
            other_sections = [s for s in other_sections if s not in section_keywords]
            
            if len(cleaned_line) < 40 and header_pattern.match(cleaned_line):
                if any(re.search(rf'\b{os_kw}\b', cleaned_line.lower()) for os_kw in other_sections):
                    break
            
            section_text.append(line)
            
    return "\n".join(section_text).strip()

def analyze_resume_against_job(job_title, job_role, skills_list, experience_required, raw_resume_text):
    """
    Compares the resume text against job details across 4 categories and returns scores and details.
    """
    cleaned_resume = clean_text(raw_resume_text)
    
    # 1. Candidate Name Extraction
    candidate_name = extract_candidate_name(raw_resume_text)
    
    # --- CATEGORY 1: Resume Skills Matching ---
    # Keyword overlap
    matched_skills = []
    missing_skills = []
    
    for skill in skills_list:
        # Use word boundaries for skills to prevent partial word matches (e.g. "git" matching "digital")
        # Handle special characters in skills like C++, .NET, C#
        escaped_skill = re.escape(skill)
        # Adapt boundaries for special chars
        if re.search(r'[^a-zA-Z0-9]', skill):
            pattern = rf'{escaped_skill}'
        else:
            pattern = rf'\b{escaped_skill}\b'
            
        if re.search(pattern, cleaned_resume):
            matched_skills.append(skill)
        else:
            missing_skills.append(skill)
            
    keyword_match_ratio = len(matched_skills) / len(skills_list) if skills_list else 1.0
    
    # Context Similarity of resume to job skills + title + role
    job_profile_text = f"{job_title} {job_role} {' '.join(skills_list)}"
    cleaned_job_profile = clean_text(job_profile_text)
    
    cosine_sim = 0.0
    model_loaded = False
    
    try:
        model = get_embedding_model()
        if model is not None:
            # Generate dense embeddings
            embeddings = model.encode([cleaned_job_profile, cleaned_resume], convert_to_numpy=True)
            # Compute cosine similarity
            cosine_sim = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            model_loaded = True
    except Exception:
        pass
        
    # Fallback to TF-IDF if model failed to load/encode
    if not model_loaded:
        try:
            vectorizer = TfidfVectorizer(stop_words='english')
            tfidf = vectorizer.fit_transform([cleaned_job_profile, cleaned_resume])
            cosine_sim = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        except Exception:
            cosine_sim = 0.0
        
    # Skills Match Score is 70% keyword overlap + 30% contextual similarity
    skills_score = (0.7 * keyword_match_ratio + 0.3 * cosine_sim) * 100
    skills_score = min(max(skills_score, 0.0), 100.0)
    
    skills_details = {
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "cosine_similarity": round(float(cosine_sim) * 100, 1),
        "keyword_percentage": round(keyword_match_ratio * 100, 1)
    }
    
    # --- CATEGORY 2: Experience Understanding ---
    parsed_exp = parse_years_of_experience(cleaned_resume, raw_resume_text)
    
    # Score calculation
    if experience_required == 0:
        exp_score = 100.0
    else:
        # Linear scoring, capped at 100
        exp_score = (parsed_exp / experience_required) * 100
        exp_score = min(max(exp_score, 0.0), 100.0)
        
    # Check if job title keywords appear in resume
    role_words = set(clean_text(job_title).split()) - {'developer', 'engineer', 'manager', 'specialist', 'sr', 'jr', 'lead', 'senior', 'junior', 'associate', 'web', 'software'}
    matched_role_words = [w for w in role_words if w in cleaned_resume]
    role_fit = "High" if len(matched_role_words) >= max(1, len(role_words)//2) else "Medium" if matched_role_words else "Low"
    
    experience_details = {
        "years_required": experience_required,
        "years_found": round(parsed_exp, 1),
        "role_fit": role_fit,
        "meets_requirements": parsed_exp >= experience_required
    }
    
    # --- CATEGORY 3: Project Analysis ---
    # Extract Projects section
    projects_text = extract_section(raw_resume_text, ['projects', 'personal projects', 'academic projects', 'key projects', 'selected projects'])
    
    project_sim = 0.0
    project_found = False
    
    if projects_text and len(projects_text) > 50:
        project_found = True
        cleaned_projects = clean_text(projects_text)
        project_model_loaded = False
        try:
            model = get_embedding_model()
            if model is not None:
                p_embeddings = model.encode([cleaned_job_profile, cleaned_projects], convert_to_numpy=True)
                project_sim = cosine_similarity([p_embeddings[0]], [p_embeddings[1]])[0][0]
                project_model_loaded = True
        except Exception:
            pass
            
        if not project_model_loaded:
            try:
                p_vectorizer = TfidfVectorizer(stop_words='english')
                p_tfidf = p_vectorizer.fit_transform([cleaned_job_profile, cleaned_projects])
                project_sim = cosine_similarity(p_tfidf[0:1], p_tfidf[1:2])[0][0]
            except Exception:
                project_sim = 0.0
            
        # Scale score: semantic embeddings score maps linearly from 0.1 to 0.8, TF-IDF is boosted
        if project_model_loaded:
            project_score = min(max((project_sim - 0.1) / 0.7 * 100, 0.0), 100.0)
        else:
            project_score = min(project_sim * 150, 100.0)
    else:
        project_score = 0.0
        
    project_details = {
        "section_found": project_found,
        "project_text_snippet": projects_text[:300] + "..." if project_found and len(projects_text) > 300 else projects_text,
        "relevance_score": round(float(project_sim) * 100, 1) if project_found else 0.0
    }
    
    # --- CATEGORY 4: Education Checking ---
    # Extract Education section
    education_text = extract_section(raw_resume_text, ['education', 'academics', 'academic details', 'qualifications', 'credentials'])
    if not education_text or len(education_text) < 30:
        # Fallback to whole resume text
        education_text = raw_resume_text
        
    cleaned_edu = clean_text(education_text)
    
    # Define degree levels and match weights
    degrees = {
        "phd": ["phd", "ph.d", "doctor of philosophy", "doctorate"],
        "masters": ["ms", "m.s.", "msc", "m.sc", "m.tech", "mtech", "mba", "master"],
        "bachelors": ["bs", "b.s.", "bsc", "b.sc", "b.tech", "btech", "be", "b.e.", "ba", "b.a.", "bachelor"],
        "diploma": ["diploma", "associate degree"]
    }
    
    candidate_degrees = []
    for deg_level, aliases in degrees.items():
        for alias in aliases:
            escaped_alias = re.escape(alias)
            if re.search(rf'\b{escaped_alias}\b', cleaned_edu):
                candidate_degrees.append(deg_level)
                break # move to next degree level
                
    # Detect job required education from job role / description
    required_edu = "bachelors" # default standard
    job_text_lower = cleaned_job_profile
    if any(alias in job_text_lower for alias in degrees["phd"]):
        required_edu = "phd"
    elif any(alias in job_text_lower for alias in degrees["masters"]):
        required_edu = "masters"
    elif any(alias in job_text_lower for alias in degrees["diploma"]):
        required_edu = "diploma"
        
    # Check match level
    degree_hierarchy = ["diploma", "bachelors", "masters", "phd"]
    
    if not candidate_degrees:
        edu_score = 40.0 # Standard partial score for no explicit edu section but text exists
        match_status = "No explicit degree found"
    else:
        # Find highest candidate degree index
        candidate_highest_idx = max(degree_hierarchy.index(d) for d in candidate_degrees)
        required_idx = degree_hierarchy.index(required_edu)
        
        if candidate_highest_idx >= required_idx:
            edu_score = 100.0
            match_status = f"Meets or exceeds requirement ({degree_hierarchy[candidate_highest_idx].title()} vs {required_edu.title()})"
        else:
            edu_score = 70.0
            match_status = f"Below requirement ({degree_hierarchy[candidate_highest_idx].title()} vs {required_edu.title()})"
            
    education_details = {
        "detected_degrees": [d.title() for d in candidate_degrees] if candidate_degrees else ["None Found"],
        "required_education_level": required_edu.title(),
        "match_status": match_status
    }
    
    # --- OVERALL AGGREGATOR ---
    # Default weights: Skills 40%, Experience 25%, Projects 20%, Education 15%
    overall_score = (
        0.40 * skills_score +
        0.25 * exp_score +
        0.20 * project_score +
        0.15 * edu_score
    )
    overall_score = round(min(max(overall_score, 0.0), 100.0), 1)
    
    return {
        "candidate_name": candidate_name,
        "match_score": overall_score,
        "skills_match_score": round(skills_score, 1),
        "experience_score": round(exp_score, 1),
        "project_score": round(project_score, 1),
        "education_score": round(edu_score, 1),
        "skills_match_details": skills_details,
        "experience_details": experience_details,
        "project_analysis_details": project_details,
        "education_check_details": education_details
    }
