"""Tools for the ATS Agent.

This module provides LangChain tools that the ATS agent can use
for document processing, analysis, and other specialized tasks.
"""

from typing import List, Dict, Any, Optional
import re
import os
from pathlib import Path

from langchain_core.tools import tool
from langchain_core.pydantic_v1 import BaseModel, Field

from ats_agent.src.utils.document_extract import extract_plain_text
from ats_agent.src.utils.text_heuristics import ResumeTextHeuristics

from ats_agent.src.core.resume_structure.runner import (
    RESUME_SECTIONS,
    run_github_project_selection,
    run_resume_evaluation,
    run_resume_section_parse,
)
from ats_agent.src.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentProcessingInput(BaseModel):
    """Input for document processing tool."""
    file_path: str = Field(description="Path to the document file")


class TextAnalysisInput(BaseModel):
    """Input for text analysis tool."""
    text: str = Field(description="Text content to analyze")


class KeywordMatchingInput(BaseModel):
    """Input for keyword matching tool."""
    resume_text: str = Field(description="Resume text content")
    job_description: str = Field(description="Job description text")


class SkillsExtractionInput(BaseModel):
    """Input for skills extraction tool."""
    text: str = Field(description="Text to extract skills from")


class ResumeJsonSectionInput(BaseModel):
    """Input for structured JSON Resume section extraction."""
    resume_markdown: str = Field(description="Resume body as markdown or plain text")
    section: str = Field(
        description=(
            "Section key: basics, work, education, skills, projects, or awards"
        )
    )


class ResumeTechnicalEvalInput(BaseModel):
    """Input for fairness-aware technical resume scorecard (JSON)."""
    resume_markdown: str = Field(description="Resume text or markdown to score")


class ResumeGithubShortlistInput(BaseModel):
    """Input for GitHub repository shortlisting from structured JSON."""
    projects_data: str = Field(
        description=(
            "JSON string: array of repository objects the model should rank "
            "(e.g. name, url, stars, commit counts, descriptions)"
        )
    )


@tool("process_document", args_schema=DocumentProcessingInput)
def process_document(file_path: str) -> Dict[str, Any]:
    """Process a document (PDF, DOCX, or TXT) and extract text content.
    
    This tool can handle multiple document formats and return structured
    text content for further analysis.
    
    Args:
        file_path: Path to the document file
        
    Returns:
        Dictionary containing extracted text and metadata
    """
    try:
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "text": "",
                "metadata": {}
            }
        
        text = extract_plain_text(file_path)
        
        # Get file metadata
        file_info = Path(file_path)
        metadata = {
            "file_name": file_info.name,
            "file_size": file_info.stat().st_size,
            "file_extension": file_info.suffix,
            "word_count": len(text.split()),
            "char_count": len(text)
        }
        
        logger.info(f"Successfully processed document: {file_path}")
        
        return {
            "success": True,
            "text": text,
            "metadata": metadata,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Error processing document {file_path}: {e}")
        return {
            "success": False,
            "error": str(e),
            "text": "",
            "metadata": {}
        }


@tool("analyze_text_structure", args_schema=TextAnalysisInput)
def analyze_text_structure(text: str) -> Dict[str, Any]:
    """Analyze the structure and sections of resume text.
    
    This tool identifies different sections of a resume and provides
    structural analysis for optimization recommendations.
    
    Args:
        text: Resume text to analyze
        
    Returns:
        Dictionary containing section analysis and structure insights
    """
    try:
        heuristics = ResumeTextHeuristics()

        # Analyze sections
        sections = heuristics.analyze_resume_sections(text)
        
        # Extract keywords  
        keywords = heuristics.extract_keywords(text)
        
        # Basic text statistics
        lines = text.split('\n')
        paragraphs = text.split('\n\n')
        sentences = text.split('.')
        words = text.split()
        
        # Section analysis
        section_stats = {}
        for section_name, section_content in sections.items():
            if section_content.strip():
                section_stats[section_name] = {
                    "word_count": len(section_content.split()),
                    "line_count": len(section_content.split('\n')),
                    "has_content": True
                }
            else:
                section_stats[section_name] = {
                    "word_count": 0,
                    "line_count": 0,
                    "has_content": False
                }
        
        result = {
            "success": True,
            "sections": sections,
            "section_stats": section_stats,
            "keywords": keywords[:20],  # Top 20 keywords
            "text_stats": {
                "total_words": len(words),
                "total_lines": len(lines),
                "total_paragraphs": len([p for p in paragraphs if p.strip()]),
                "total_sentences": len([s for s in sentences if s.strip()]),
                "avg_words_per_sentence": len(words) / max(1, len(sentences))
            }
        }
        
        logger.info("Text structure analysis completed")
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing text structure: {e}")
        return {
            "success": False,
            "error": str(e),
            "sections": {},
            "keywords": [],
            "text_stats": {}
        }


@tool("match_keywords", args_schema=KeywordMatchingInput)
def match_keywords(resume_text: str, job_description: str) -> Dict[str, Any]:
    """Perform keyword matching between resume and job description.
    
    This tool uses both exact and fuzzy matching algorithms to identify
    keyword alignment and gaps between resume and job requirements.
    
    Args:
        resume_text: Text content of the resume
        job_description: Job description text
        
    Returns:
        Dictionary containing keyword analysis results
    """
    try:
        heuristics = ResumeTextHeuristics()

        # Perform keyword matching
        matched, missing, score = heuristics.calculate_keyword_match(
            resume_text, job_description
        )

        # Extract all keywords for analysis
        resume_keywords = heuristics.extract_keywords(resume_text)
        job_keywords = heuristics.extract_keywords(job_description)
        
        # Calculate additional metrics
        total_job_keywords = len(job_keywords)
        total_resume_keywords = len(resume_keywords)
        unique_resume_keywords = len(set(resume_keywords) - set(job_keywords))
        
        result = {
            "success": True,
            "match_score": score,
            "matched_keywords": matched[:15],  # Top 15 matches
            "missing_keywords": missing[:15],  # Top 15 missing
            "all_job_keywords": job_keywords,
            "all_resume_keywords": resume_keywords,
            "stats": {
                "total_job_keywords": total_job_keywords,
                "total_resume_keywords": total_resume_keywords,
                "matched_count": len(matched),
                "missing_count": len(missing),
                "match_percentage": score,
                "unique_resume_keywords": unique_resume_keywords
            }
        }
        
        logger.info(f"Keyword matching completed - score: {score}%")
        return result
        
    except Exception as e:
        logger.error(f"Error in keyword matching: {e}")
        return {
            "success": False,
            "error": str(e),
            "match_score": 0,
            "matched_keywords": [],
            "missing_keywords": [],
            "stats": {}
        }


@tool("extract_skills", args_schema=SkillsExtractionInput)
def extract_skills(text: str) -> Dict[str, Any]:
    """Extract technical and soft skills from text content.
    
    This tool identifies various types of skills including programming
    languages, frameworks, tools, and soft skills from resume or job text.
    
    Args:
        text: Text content to analyze for skills
        
    Returns:
        Dictionary containing categorized skills and analysis
    """
    try:
        heuristics = ResumeTextHeuristics()

        # Extract skills using lexicon + capitalized tokens
        all_skills = heuristics.extract_skills_from_text(text)
        
        # Categorize skills
        technical_skills = []
        programming_languages = []
        frameworks_tools = []
        soft_skills = []
        
        # Programming languages
        prog_patterns = [
            'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 
            'rust', 'php', 'ruby', 'swift', 'kotlin', 'scala', 'r', 'matlab'
        ]
        
        # Frameworks and tools
        framework_patterns = [
            'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'git', 'jenkins'
        ]
        
        # Soft skills patterns
        soft_skill_patterns = [
            'leadership', 'communication', 'teamwork', 'management', 'analytical',
            'problem solving', 'creative', 'organized', 'detail oriented'
        ]
        
        text_lower = text.lower()
        
        # Categorize found skills
        for skill in all_skills:
            skill_lower = skill.lower()
            
            if any(prog in skill_lower for prog in prog_patterns):
                programming_languages.append(skill)
            elif any(fw in skill_lower for fw in framework_patterns):
                frameworks_tools.append(skill)
            elif any(soft in skill_lower for soft in soft_skill_patterns):
                soft_skills.append(skill)
            else:
                technical_skills.append(skill)
        
        # Additional skill detection from text
        for pattern in prog_patterns:
            if pattern in text_lower and pattern not in [s.lower() for s in programming_languages]:
                programming_languages.append(pattern.title())
        
        for pattern in framework_patterns:
            if pattern in text_lower and pattern not in [s.lower() for s in frameworks_tools]:
                frameworks_tools.append(pattern.title())
        
        result = {
            "success": True,
            "all_skills": all_skills,
            "categorized_skills": {
                "programming_languages": list(set(programming_languages)),
                "frameworks_tools": list(set(frameworks_tools)),
                "technical_skills": list(set(technical_skills)),
                "soft_skills": list(set(soft_skills))
            },
            "skills_count": {
                "total": len(all_skills),
                "programming": len(set(programming_languages)),
                "frameworks": len(set(frameworks_tools)),
                "technical": len(set(technical_skills)),
                "soft": len(set(soft_skills))
            }
        }
        
        logger.info(f"Skills extraction completed - found {len(all_skills)} skills")
        return result
        
    except Exception as e:
        logger.error(f"Error extracting skills: {e}")
        return {
            "success": False,
            "error": str(e),
            "all_skills": [],
            "categorized_skills": {},
            "skills_count": {}
        }


@tool("calculate_ats_score")
def calculate_ats_score(
    keyword_score: int,
    skills_match_score: int = 0,
    format_score: int = 85,
    experience_score: int = 0
) -> Dict[str, Any]:
    """Calculate comprehensive ATS compatibility score.
    
    This tool combines multiple factors to generate an overall
    ATS compatibility score with detailed breakdown.
    
    Args:
        keyword_score: Score from keyword matching (0-100)
        skills_match_score: Score from skills analysis (0-100)
        format_score: Score from format analysis (0-100, default 85)
        experience_score: Score from experience relevance (0-100)
        
    Returns:
        Dictionary containing comprehensive scoring breakdown
    """
    try:
        # Weighted scoring algorithm
        weights = {
            "keyword": 0.40,    # 40% weight
            "skills": 0.25,     # 25% weight  
            "experience": 0.20,  # 20% weight
            "format": 0.15      # 15% weight
        }
        
        # Calculate weighted score
        overall_score = (
            keyword_score * weights["keyword"] +
            skills_match_score * weights["skills"] +
            experience_score * weights["experience"] +
            format_score * weights["format"]
        )
        
        overall_score = min(100, max(0, int(overall_score)))
        
        # Determine grade
        if overall_score >= 95: grade = "A+"
        elif overall_score >= 90: grade = "A"
        elif overall_score >= 85: grade = "B+"
        elif overall_score >= 80: grade = "B"
        elif overall_score >= 75: grade = "C+"
        elif overall_score >= 70: grade = "C"
        elif overall_score >= 65: grade = "D+"
        elif overall_score >= 60: grade = "D"
        else: grade = "F"
        
        # Calculate percentile (simplified)
        percentile = min(99, overall_score + 5)
        
        # Score interpretation
        if overall_score >= 90:
            interpretation = "Excellent ATS compatibility - likely to pass most systems"
        elif overall_score >= 80:
            interpretation = "Good ATS compatibility - minor optimizations recommended"
        elif overall_score >= 70:
            interpretation = "Moderate ATS compatibility - improvements needed"
        elif overall_score >= 60:
            interpretation = "Below average - significant optimization required"
        else:
            interpretation = "Poor ATS compatibility - major restructuring needed"
        
        result = {
            "success": True,
            "overall_score": overall_score,
            "grade": grade,
            "percentile": percentile,
            "interpretation": interpretation,
            "component_scores": {
                "keyword_score": keyword_score,
                "skills_score": skills_match_score,
                "experience_score": experience_score,
                "format_score": format_score
            },
            "weights_used": weights,
            "recommendations": []
        }
        
        # Add specific recommendations based on scores
        if keyword_score < 70:
            result["recommendations"].append(
                "Focus on incorporating more relevant keywords from job description"
            )
        
        if skills_match_score < 70:
            result["recommendations"].append(
                "Highlight additional skills that match job requirements"
            )
        
        if experience_score < 70:
            result["recommendations"].append(
                "Better emphasize relevant experience and achievements"
            )
        
        if format_score < 80:
            result["recommendations"].append(
                "Improve resume format for better ATS compatibility"
            )
        
        logger.info(f"ATS score calculated: {overall_score}/100 ({grade})")
        return result
        
    except Exception as e:
        logger.error(f"Error calculating ATS score: {e}")
        return {
            "success": False,
            "error": str(e),
            "overall_score": 0,
            "grade": "F",
            "percentile": 0,
            "interpretation": "Score calculation failed"
        }


@tool("resume_list_json_sections")
def resume_list_json_sections() -> Dict[str, Any]:
    """List section keys supported by resume_parse_json_section."""
    return {
        "success": True,
        "sections": list(RESUME_SECTIONS),
        "description": (
            "Use one of these values as `section` with resume text to extract "
            "a single JSON Resume–style block."
        ),
    }


@tool("resume_parse_json_section", args_schema=ResumeJsonSectionInput)
def resume_parse_json_section(resume_markdown: str, section: str) -> Dict[str, Any]:
    """Extract one JSON Resume section (LLM); uses this product's own prompt templates."""
    return run_resume_section_parse(
        resume_markdown=resume_markdown, section=section.strip().lower()
    )


@tool("resume_technical_evaluation", args_schema=ResumeTechnicalEvalInput)
def resume_technical_evaluation(resume_markdown: str) -> Dict[str, Any]:
    """Return a fairness-aware technical scorecard JSON for the resume (LLM)."""
    return run_resume_evaluation(resume_markdown=resume_markdown)


@tool("resume_github_repo_shortlist", args_schema=ResumeGithubShortlistInput)
def resume_github_repo_shortlist(projects_data: str) -> Dict[str, Any]:
    """Rank up to seven repositories from structured JSON input (LLM)."""
    return run_github_project_selection(projects_data=projects_data)


def get_ats_tools() -> List:
    """Get all available ATS tools for the agent.
    
    Returns:
        List of LangChain tools for ATS functionality
    """
    return [
        process_document,
        analyze_text_structure,
        match_keywords,
        extract_skills,
        calculate_ats_score,
        resume_list_json_sections,
        resume_parse_json_section,
        resume_technical_evaluation,
        resume_github_repo_shortlist,
    ]