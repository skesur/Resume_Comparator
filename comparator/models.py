from django.db import models

class JobPosting(models.Model):
    job_title = models.CharField(max_length=255, verbose_name="Job Title")
    job_role = models.CharField(max_length=255, verbose_name="Job Role/Description")
    skills_required = models.TextField(verbose_name="Required Skills", help_text="Comma-separated list of skills")
    experience_required = models.PositiveIntegerField(verbose_name="Required Experience (Years)", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.job_title} ({self.experience_required} yrs exp)"

    def get_skills_list(self):
        """Returns the skills as a cleaned list of lower-case strings."""
        if not self.skills_required:
            return []
        return [s.strip().lower() for s in self.skills_required.split(',') if s.strip()]


class ResumeSubmission(models.Model):
    job_posting = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name="submissions")
    candidate_name = models.CharField(max_length=255, blank=True, default="Unknown Candidate")
    resume_file = models.FileField(upload_to="resumes/")
    
    # Matching Scores (out of 100)
    match_score = models.FloatField(default=0.0, verbose_name="Overall Match Score")
    skills_match_score = models.FloatField(default=0.0, verbose_name="Skills Match Score")
    experience_score = models.FloatField(default=0.0, verbose_name="Experience Score")
    project_score = models.FloatField(default=0.0, verbose_name="Project Analysis Score")
    education_score = models.FloatField(default=0.0, verbose_name="Education Check Score")

    # Detailed Analysis JSON
    skills_match_details = models.JSONField(default=dict, blank=True)
    experience_details = models.JSONField(default=dict, blank=True)
    project_analysis_details = models.JSONField(default=dict, blank=True)
    education_check_details = models.JSONField(default=dict, blank=True)

    processed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.candidate_name} - {self.job_posting.job_title} ({self.match_score}%)"
