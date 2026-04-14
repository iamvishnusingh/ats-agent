#!/usr/bin/env python3
"""Test script for the ATS Agent"""

from ats_agent import ATSAgent

def test_ats_agent():
    """Test the ATS Agent with sample data"""
    print("🧪 Testing ATS Resume Reviewer Agent")
    print("=" * 50)
    
    # Initialize agent
    agent = ATSAgent()
    
    # Load test data
    try:
        with open('test_data/sample_resume.txt', 'r') as f:
            resume_text = f.read()
        
        with open('test_data/sample_job_description.txt', 'r') as f:
            job_desc = f.read()
        
        print("✅ Test data loaded successfully")
        
        # Run analysis
        print("\n🔍 Running ATS analysis...")
        results = agent.analyze_resume(resume_text, job_desc, is_file_path=False)
        
        # Display results
        output = agent.format_output(results, resume_text, job_desc)
        print(output)
        
        print(f"\n📊 Analysis Summary:")
        print(f"   • Match Score: {results.match_score}/100")
        print(f"   • Matched Keywords: {len(results.matched_keywords)}")
        print(f"   • Missing Keywords: {len(results.missing_keywords)}")
        print(f"   • Skills Found: {len(results.skills_present)}")
        print(f"   • Recommendations: {len(results.recommendations)}")
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")

if __name__ == "__main__":
    test_ats_agent()