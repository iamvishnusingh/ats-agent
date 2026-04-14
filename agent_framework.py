#!/usr/bin/env python3
"""
Advanced ATS Agent Framework Implementation
Using LangChain-style agent architecture with structured skills
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from datetime import datetime

class AgentSkillType(Enum):
    """Types of agent skills"""
    DOCUMENT_PROCESSING = "document_processing"
    TEXT_ANALYSIS = "text_analysis"
    KEYWORD_MATCHING = "keyword_matching"
    SCORING = "scoring"
    RECOMMENDATION = "recommendation"
    OUTPUT_FORMATTING = "output_formatting"

@dataclass
class AgentSkill:
    """Represents a single agent skill/capability"""
    name: str
    skill_type: AgentSkillType
    description: str
    input_types: List[str]
    output_type: str
    dependencies: List[str] = field(default_factory=list)
    enabled: bool = True
    
    def __post_init__(self):
        self.created_at = datetime.now()
        self.execution_count = 0

@dataclass
class AgentMemory:
    """Agent's memory system"""
    short_term: Dict[str, Any] = field(default_factory=dict)
    long_term: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)

class BaseAgentSkill(ABC):
    """Abstract base class for all agent skills"""
    
    def __init__(self, skill_config: AgentSkill):
        self.config = skill_config
        self.logger = logging.getLogger(f"skill.{skill_config.name}")
        
    @abstractmethod
    def execute(self, inputs: Dict[str, Any], memory: AgentMemory) -> Dict[str, Any]:
        """Execute the skill with given inputs and memory"""
        pass
    
    @abstractmethod
    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate if inputs are correct for this skill"""
        pass

class DocumentProcessingSkill(BaseAgentSkill):
    """Skill for processing documents (PDF, DOCX, TXT)"""
    
    def __init__(self):
        skill_config = AgentSkill(
            name="document_processor",
            skill_type=AgentSkillType.DOCUMENT_PROCESSING,
            description="Extracts text content from PDF, DOCX, and plain text files",
            input_types=["file_path", "file_content"],
            output_type="extracted_text",
            dependencies=["pdfplumber", "python-docx"]
        )
        super().__init__(skill_config)
        
    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        return "file_path" in inputs or "file_content" in inputs
    
    def execute(self, inputs: Dict[str, Any], memory: AgentMemory) -> Dict[str, Any]:
        from ats_agent.src.utils.document_extract import extract_plain_text

        if "file_path" in inputs:
            text = extract_plain_text(inputs["file_path"])
        else:
            text = inputs["file_content"]
            
        memory.context["document_text"] = text
        
        return {
            "extracted_text": text,
            "word_count": len(text.split()),
            "char_count": len(text),
            "status": "success"
        }

class TextAnalysisSkill(BaseAgentSkill):
    """Skill for analyzing and preprocessing text"""
    
    def __init__(self):
        skill_config = AgentSkill(
            name="text_analyzer",
            skill_type=AgentSkillType.TEXT_ANALYSIS,
            description="Analyzes text structure, extracts sections, and preprocesses content",
            input_types=["text"],
            output_type="analysis_result",
            dependencies=["nltk"]
        )
        super().__init__(skill_config)
        
    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        return "text" in inputs and len(inputs["text"].strip()) > 0
    
    def execute(self, inputs: Dict[str, Any], memory: AgentMemory) -> Dict[str, Any]:
        from ats_agent.src.utils.text_heuristics import ResumeTextHeuristics

        heuristics = ResumeTextHeuristics()
        text = inputs["text"]

        # Extract keywords and sections
        keywords = heuristics.extract_keywords(text)
        sections = heuristics.analyze_resume_sections(text)
        skills = heuristics.extract_skills_from_text(text)
        
        analysis = {
            "keywords": keywords,
            "sections": sections,
            "skills": skills,
            "text_stats": {
                "sentences": len(text.split('.')),
                "paragraphs": len(text.split('\n\n')),
                "avg_words_per_sentence": len(text.split()) / max(1, len(text.split('.')))
            }
        }
        
        memory.context["text_analysis"] = analysis
        
        return analysis

class KeywordMatchingSkill(BaseAgentSkill):
    """Skill for matching keywords between resume and job description"""
    
    def __init__(self):
        skill_config = AgentSkill(
            name="keyword_matcher",
            skill_type=AgentSkillType.KEYWORD_MATCHING,
            description="Performs exact and fuzzy keyword matching between texts",
            input_types=["resume_text", "job_description"],
            output_type="keyword_analysis",
            dependencies=["fuzzywuzzy", "sklearn"]
        )
        super().__init__(skill_config)
        
    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        return "resume_text" in inputs and "job_description" in inputs
    
    def execute(self, inputs: Dict[str, Any], memory: AgentMemory) -> Dict[str, Any]:
        from ats_agent.src.utils.text_heuristics import ResumeTextHeuristics

        heuristics = ResumeTextHeuristics()
        matched, missing, score = heuristics.calculate_keyword_match(
            inputs["resume_text"],
            inputs["job_description"],
        )

        result = {
            "matched_keywords": matched,
            "missing_keywords": missing,
            "match_score": score,
            "total_job_keywords": len(heuristics.extract_keywords(inputs["job_description"])),
            "match_ratio": score / 100
        }
        
        memory.context["keyword_analysis"] = result
        return result

class ScoringSkill(BaseAgentSkill):
    """Skill for generating comprehensive ATS scores"""
    
    def __init__(self):
        skill_config = AgentSkill(
            name="ats_scorer",
            skill_type=AgentSkillType.SCORING,
            description="Calculates comprehensive ATS compatibility scores",
            input_types=["keyword_analysis", "text_analysis"],
            output_type="ats_scores",
            dependencies=["scikit-learn"]
        )
        super().__init__(skill_config)
        
    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        return "keyword_analysis" in inputs
    
    def execute(self, inputs: Dict[str, Any], memory: AgentMemory) -> Dict[str, Any]:
        keyword_analysis = inputs["keyword_analysis"]
        
        # Base score from keyword matching
        base_score = keyword_analysis["match_score"]
        
        # Adjust based on other factors
        adjustments = {
            "keyword_density": 0,
            "skills_match": 0,
            "experience_quality": 0,
            "format_quality": 5  # Default bonus for clean format
        }
        
        # Calculate final score
        final_score = min(100, base_score + sum(adjustments.values()))
        
        scores = {
            "overall_score": final_score,
            "keyword_score": keyword_analysis["match_score"],
            "adjustments": adjustments,
            "grade": self._get_grade(final_score),
            "percentile": self._calculate_percentile(final_score)
        }
        
        memory.context["scores"] = scores
        return scores
    
    def _get_grade(self, score: int) -> str:
        if score >= 90: return "A+"
        elif score >= 85: return "A"
        elif score >= 80: return "B+"
        elif score >= 75: return "B"
        elif score >= 70: return "C+"
        elif score >= 65: return "C"
        elif score >= 60: return "D"
        else: return "F"
    
    def _calculate_percentile(self, score: int) -> int:
        # Simplified percentile calculation
        return min(99, score + 10)

class RecommendationSkill(BaseAgentSkill):
    """Skill for generating improvement recommendations"""
    
    def __init__(self):
        skill_config = AgentSkill(
            name="recommendation_engine",
            skill_type=AgentSkillType.RECOMMENDATION,
            description="Generates personalized improvement recommendations",
            input_types=["keyword_analysis", "text_analysis", "scores"],
            output_type="recommendations",
            dependencies=[]
        )
        super().__init__(skill_config)
        
    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        return "keyword_analysis" in inputs
    
    def execute(self, inputs: Dict[str, Any], memory: AgentMemory) -> Dict[str, Any]:
        keyword_analysis = inputs["keyword_analysis"]
        text_analysis = inputs.get("text_analysis", {})
        scores = inputs.get("scores", {})
        
        recommendations = {
            "priority_high": [],
            "priority_medium": [],
            "priority_low": [],
            "action_plan": []
        }
        
        # High priority recommendations
        if keyword_analysis["match_score"] < 60:
            recommendations["priority_high"].append(
                f"Add missing keywords: {', '.join(keyword_analysis['missing_keywords'][:5])}"
            )
        
        if scores and scores.get("overall_score", 0) < 70:
            recommendations["priority_high"].append(
                "Restructure resume to better align with job requirements"
            )
        
        # Medium priority
        missing_keywords = keyword_analysis.get("missing_keywords", [])
        if len(missing_keywords) > 10:
            recommendations["priority_medium"].append(
                "Consider adding industry-specific terminology"
            )
        
        # Low priority
        recommendations["priority_low"].append(
            "Optimize formatting for ATS compatibility"
        )
        
        # Action plan
        recommendations["action_plan"] = [
            "1. Incorporate top 5 missing keywords naturally",
            "2. Add quantified achievements",
            "3. Use strong action verbs",
            "4. Optimize section headers",
            "5. Proofread for ATS-friendly formatting"
        ]
        
        memory.context["recommendations"] = recommendations
        return recommendations

class OutputFormattingSkill(BaseAgentSkill):
    """Skill for formatting final output"""
    
    def __init__(self):
        skill_config = AgentSkill(
            name="output_formatter",
            skill_type=AgentSkillType.OUTPUT_FORMATTING,
            description="Formats analysis results into user-friendly output",
            input_types=["all_analysis_data"],
            output_type="formatted_report",
            dependencies=[]
        )
        super().__init__(skill_config)
        
    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        return len(inputs) > 0
    
    def execute(self, inputs: Dict[str, Any], memory: AgentMemory) -> Dict[str, Any]:
        # Get all data from memory context
        context = memory.context
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "overall_score": context.get("scores", {}).get("overall_score", 0),
                "grade": context.get("scores", {}).get("grade", "N/A"),
                "total_recommendations": len(context.get("recommendations", {}).get("action_plan", []))
            },
            "detailed_analysis": context,
            "formatted_output": self._generate_formatted_text(context)
        }
        
        return report
    
    def _generate_formatted_text(self, context: Dict[str, Any]) -> str:
        scores = context.get("scores", {})
        keyword_analysis = context.get("keyword_analysis", {})
        recommendations = context.get("recommendations", {})
        
        output = f"""
# ATS ANALYSIS REPORT
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## OVERALL SCORE: {scores.get('overall_score', 0)}/100 ({scores.get('grade', 'N/A')})

## KEYWORD ANALYSIS
✅ Matched: {len(keyword_analysis.get('matched_keywords', []))} keywords
❌ Missing: {len(keyword_analysis.get('missing_keywords', []))} keywords

## TOP RECOMMENDATIONS
{chr(10).join(['• ' + rec for rec in recommendations.get('priority_high', [])])}

## ACTION PLAN
{chr(10).join(recommendations.get('action_plan', []))}
"""
        return output

class ATSAgentFramework:
    """Main ATS Agent Framework orchestrating all skills"""
    
    def __init__(self):
        self.skills: Dict[str, BaseAgentSkill] = {}
        self.memory = AgentMemory()
        self.execution_history: List[Dict[str, Any]] = []
        
        # Setup logging first
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("ats_agent_framework")
        
        # Initialize all skills
        self._initialize_skills()
    
    def _initialize_skills(self):
        """Initialize all available skills"""
        skills = [
            DocumentProcessingSkill(),
            TextAnalysisSkill(),
            KeywordMatchingSkill(),
            ScoringSkill(),
            RecommendationSkill(),
            OutputFormattingSkill()
        ]
        
        for skill in skills:
            self.skills[skill.config.name] = skill
            self.logger.info(f"Initialized skill: {skill.config.name}")
    
    def get_available_skills(self) -> Dict[str, AgentSkill]:
        """Get all available skills and their configurations"""
        return {name: skill.config for name, skill in self.skills.items()}
    
    def execute_skill(self, skill_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific skill"""
        if skill_name not in self.skills:
            raise ValueError(f"Skill '{skill_name}' not found")
        
        skill = self.skills[skill_name]
        
        if not skill.validate_inputs(inputs):
            raise ValueError(f"Invalid inputs for skill '{skill_name}'")
        
        # Record execution
        execution_record = {
            "skill_name": skill_name,
            "timestamp": datetime.now().isoformat(),
            "inputs": inputs,
            "status": "started"
        }
        
        try:
            result = skill.execute(inputs, self.memory)
            skill.config.execution_count += 1
            
            execution_record["status"] = "completed"
            execution_record["result"] = result
            
            self.execution_history.append(execution_record)
            
            return result
            
        except Exception as e:
            execution_record["status"] = "failed"
            execution_record["error"] = str(e)
            self.execution_history.append(execution_record)
            raise
    
    def analyze_resume_full_pipeline(self, resume_input: str, job_description: str, 
                                   is_file_path: bool = False) -> Dict[str, Any]:
        """Execute full ATS analysis pipeline"""
        
        try:
            # Step 1: Document Processing
            if is_file_path:
                doc_result = self.execute_skill("document_processor", {"file_path": resume_input})
                resume_text = doc_result["extracted_text"]
            else:
                resume_text = resume_input
            
            # Step 2: Text Analysis
            text_analysis = self.execute_skill("text_analyzer", {"text": resume_text})
            
            # Step 3: Keyword Matching
            keyword_analysis = self.execute_skill("keyword_matcher", {
                "resume_text": resume_text,
                "job_description": job_description
            })
            
            # Step 4: Scoring
            scores = self.execute_skill("ats_scorer", {
                "keyword_analysis": keyword_analysis,
                "text_analysis": text_analysis
            })
            
            # Step 5: Recommendations
            recommendations = self.execute_skill("recommendation_engine", {
                "keyword_analysis": keyword_analysis,
                "text_analysis": text_analysis,
                "scores": scores
            })
            
            # Step 6: Output Formatting
            final_report = self.execute_skill("output_formatter", {
                "all_data": True  # Will use memory context
            })
            
            return final_report
            
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {str(e)}")
            raise
    
    def get_memory_state(self) -> AgentMemory:
        """Get current memory state"""
        return self.memory
    
    def clear_memory(self):
        """Clear agent memory"""
        self.memory = AgentMemory()
        self.logger.info("Memory cleared")
    
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get execution history"""
        return self.execution_history

def main():
    """Demo of the ATS Agent Framework"""
    print("🤖 ATS Agent Framework Demo")
    print("=" * 50)
    
    # Initialize framework
    framework = ATSAgentFramework()
    
    # Show available skills
    print("\n📋 Available Skills:")
    skills = framework.get_available_skills()
    for name, config in skills.items():
        print(f"  • {name}: {config.description}")
    
    # Load test data
    try:
        with open('test_data/sample_resume.txt', 'r') as f:
            resume_text = f.read()
        
        with open('test_data/sample_job_description.txt', 'r') as f:
            job_desc = f.read()
        
        print("\n🔍 Running full ATS analysis pipeline...")
        
        # Execute pipeline
        result = framework.analyze_resume_full_pipeline(resume_text, job_desc, False)
        
        # Display results
        print("\n📊 Analysis Complete!")
        print(result["formatted_output"])
        
        # Show execution history
        print(f"\n📈 Executed {len(framework.get_execution_history())} skills")
        
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")

if __name__ == "__main__":
    main()