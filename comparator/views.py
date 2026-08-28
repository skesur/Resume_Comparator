from django.shortcuts import render, redirect, get_object_or_404
from .forms import ResumeCompareForm
from .models import JobPosting, ResumeSubmission
from .utils import extract_text_from_pdf, analyze_resume_against_job

def compare_resume_view(request):
    if request.method == 'POST':
        form = ResumeCompareForm(request.POST, request.FILES)
        if form.is_valid():
            # 1. Create JobPosting
            job_posting = JobPosting.objects.create(
                job_title=form.cleaned_data['job_title'],
                job_role=form.cleaned_data['job_role'],
                skills_required=form.cleaned_data['skills_required'],
                experience_required=form.cleaned_data['experience_required']
            )
            
            # 2. Create ResumeSubmission (initially empty matching details)
            submission = ResumeSubmission.objects.create(
                job_posting=job_posting,
                resume_file=form.cleaned_data['resume_file']
            )
            
            # 3. Read text from uploaded PDF
            pdf_file = submission.resume_file
            # Reset file pointer just in case
            pdf_file.seek(0)
            raw_text = extract_text_from_pdf(pdf_file)
            
            # 4. Perform AI/ML comparison
            skills_list = job_posting.get_skills_list()
            analysis_results = analyze_resume_against_job(
                job_title=job_posting.job_title,
                job_role=job_posting.job_role,
                skills_list=skills_list,
                experience_required=job_posting.experience_required,
                raw_resume_text=raw_text
            )
            
            # 5. Populate and update the submission
            submission.candidate_name = analysis_results['candidate_name']
            submission.match_score = analysis_results['match_score']
            submission.skills_match_score = analysis_results['skills_match_score']
            submission.experience_score = analysis_results['experience_score']
            submission.project_score = analysis_results['project_score']
            submission.education_score = analysis_results['education_score']
            
            submission.skills_match_details = analysis_results['skills_match_details']
            submission.experience_details = analysis_results['experience_details']
            submission.project_analysis_details = analysis_results['project_analysis_details']
            submission.education_check_details = analysis_results['education_check_details']
            
            submission.save()
            
            return redirect('comparator:compare_result', submission_id=submission.id)
    else:
        form = ResumeCompareForm()
        
    return render(request, 'comparator/compare_form.html', {'form': form})

def compare_result_view(request, submission_id):
    submission = get_object_or_404(ResumeSubmission, id=submission_id)
    job = submission.job_posting
    
    context = {
        'submission': submission,
        'job': job,
        # Parse experience details directly for easier rendering in templates
        'exp_found': submission.experience_details.get('years_found', 0),
        'exp_required': submission.experience_details.get('years_required', 0),
        'exp_meets': submission.experience_details.get('meets_requirements', False),
        'role_fit': submission.experience_details.get('role_fit', 'Medium'),
        
        # Skills lists
        'matched_skills': submission.skills_match_details.get('matched_skills', []),
        'missing_skills': submission.skills_match_details.get('missing_skills', []),
        'skills_similarity': submission.skills_match_details.get('cosine_similarity', 0.0),
        'skills_keyword_percentage': submission.skills_match_details.get('keyword_percentage', 0.0),
        
        # Projects
        'project_snippet': submission.project_analysis_details.get('project_text_snippet', ''),
        'project_section_found': submission.project_analysis_details.get('section_found', False),
        'project_relevance': submission.project_analysis_details.get('relevance_score', 0.0),
        
        # Education
        'detected_degrees': submission.education_check_details.get('detected_degrees', []),
        'required_edu': submission.education_check_details.get('required_education_level', 'Bachelors'),
        'edu_match_status': submission.education_check_details.get('match_status', ''),
    }
    
    return render(request, 'comparator/compare_result.html', context)
