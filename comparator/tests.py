from django.test import TestCase
from django.urls import reverse
from .models import JobPosting, ResumeSubmission
from .utils import clean_text, extract_candidate_name, parse_years_of_experience, extract_section, analyze_resume_against_job

class NLPUtilityTests(TestCase):
    def test_clean_text(self):
        text = "Hello   World!\nThis is a TEST."
        self.assertEqual(clean_text(text), "hello world! this is a test.")

    def test_extract_candidate_name(self):
        # A mock resume header
        raw_resume = "John Doe\nSoftware Engineer\nEmail: john@example.com\n"
        name = extract_candidate_name(raw_resume)
        self.assertEqual(name, "John Doe")

        # Fallback case
        raw_resume_no_name = "Resume\nEmail: test@example.com"
        name = extract_candidate_name(raw_resume_no_name)
        self.assertEqual(name, "Unknown Candidate")

    def test_parse_years_of_experience_direct(self):
        resume_text = "i have 5 years of experience in python and django. also worked 2 years on databases."
        cleaned = clean_text(resume_text)
        exp = parse_years_of_experience(cleaned, resume_text)
        # Should pick the max direct mention (5 years)
        self.assertEqual(exp, 5.0)

    def test_parse_years_of_experience_date_ranges(self):
        resume_raw = "Work history:\nCompany A: 2018 - 2021\nCompany B: 2021 - Present"
        # Current local year in code is assumed 2026.
        # Range 1: 2018 - 2021 = 3 years
        # Range 2: 2021 - 2026 = 5 years
        # Total sum of date ranges = 8 years
        cleaned = clean_text(resume_raw)
        exp = parse_years_of_experience(cleaned, resume_raw)
        self.assertEqual(exp, 8.0)

    def test_extract_section(self):
        resume_raw = "Summary\nI am a coder\nProjects\nProject A: Built a resume matcher using Django.\nProject B: Made a weather website.\nEducation\nB.Tech in Computer Science"
        proj_sec = extract_section(resume_raw, ['projects'])
        self.assertIn("Project A", proj_sec)
        self.assertIn("Project B", proj_sec)
        self.assertNotIn("B.Tech", proj_sec)

    def test_analyze_resume_against_job(self):
        job_title = "Python Django Developer"
        job_role = "Build web apps using Django and PostgreSQL backend"
        skills = ["python", "django", "postgresql", "docker"]
        experience_req = 3
        
        resume = """
        Jane Smith
        Python Developer
        
        Experience:
        Senior Dev: 2022 - Present
        
        Skills: Python, Django, Git, SQL, Postgresql
        
        Projects:
        Built a scalable billing application using Django and Postgresql.
        
        Education:
        B.Tech in Information Technology
        """
        
        results = analyze_resume_against_job(job_title, job_role, skills, experience_req, resume)
        
        self.assertEqual(results['candidate_name'], "Jane Smith")
        self.assertTrue(results['match_score'] > 0)
        # Python, Django, and Postgresql should be matched
        self.assertIn("python", results['skills_match_details']['matched_skills'])
        self.assertIn("django", results['skills_match_details']['matched_skills'])
        # Docker should be missing
        self.assertIn("docker", results['skills_match_details']['missing_skills'])
        # Candidate has 2022-2026 = 4 years, which meets the 3 year requirement
        self.assertTrue(results['experience_details']['meets_requirements'])

    def test_analyze_resume_no_projects(self):
        job_title = "Python Developer"
        job_role = "Web development"
        skills = ["python"]
        experience_req = 1
        
        resume = """
        Alice Green
        Python Developer
        Experience: 2 years
        Education: Bachelors in CS
        """
        results = analyze_resume_against_job(job_title, job_role, skills, experience_req, resume)
        self.assertEqual(results['project_score'], 0.0)
        self.assertFalse(results['project_analysis_details']['section_found'])


class ViewTests(TestCase):
    def test_form_view_get(self):
        response = self.client.get(reverse('comparator:compare_form'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'comparator/compare_form.html')

    def test_result_view_get(self):
        job = JobPosting.objects.create(
            job_title="Dev",
            job_role="Web",
            skills_required="python",
            experience_required=1
        )
        submission = ResumeSubmission.objects.create(
            job_posting=job,
            candidate_name="Test Candidate",
            match_score=75.0,
            skills_match_score=80.0,
            experience_score=60.0,
            project_score=70.0,
            education_score=90.0,
            skills_match_details={"matched_skills": ["python"], "missing_skills": [], "cosine_similarity": 60.0, "keyword_percentage": 100.0},
            experience_details={"years_required": 1, "years_found": 2, "role_fit": "High", "meets_requirements": True},
            project_analysis_details={"section_found": True, "project_text_snippet": "Snipp", "relevance_score": 70.0},
            education_check_details={"detected_degrees": ["Bachelors"], "required_education_level": "Bachelors", "match_status": "Meets"}
        )
        
        response = self.client.get(reverse('comparator:compare_result', args=[submission.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'comparator/compare_result.html')

