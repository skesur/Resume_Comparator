from django import forms
from django.core.exceptions import ValidationError

def validate_pdf_extension(value):
    if not value.name.endswith('.pdf'):
        raise ValidationError("Only PDF files are supported.")

class ResumeCompareForm(forms.Form):
    job_title = forms.CharField(
        max_length=255,
        label="Job Title",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Python Backend Developer'
        })
    )
    
    job_role = forms.CharField(
        label="Job Role & Description",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Describe the job role, responsibilities, and other requirements...'
        })
    )
    
    skills_required = forms.CharField(
        label="Required Skills",
        help_text="Enter skills separated by commas",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Python, Django, PostgreSQL, REST API, Git'
        })
    )
    
    experience_required = forms.IntegerField(
        label="Required Experience (Years)",
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 3'
        })
    )
    
    resume_file = forms.FileField(
        label="Upload Resume (PDF)",
        validators=[validate_pdf_extension],
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf'
        })
    )
