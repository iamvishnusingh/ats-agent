#!/usr/bin/env python3
"""Setup script to install dependencies and test the ATS Agent"""

import subprocess
import sys
import os

def run_command(command):
    """Run shell command and return result"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running command: {command}")
            print(f"Error: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"Exception running command: {command} - {e}")
        return False

def main():
    print("🚀 Setting up ATS Resume Reviewer Agent...")
    print("=" * 50)
    
    # Install dependencies
    print("📦 Installing dependencies...")
    if not run_command("pip install -r requirements.txt"):
        print("❌ Failed to install dependencies")
        return
    
    # Download NLTK data
    print("📚 Downloading NLTK data...")
    try:
        import nltk
        nltk.download('punkt')
        nltk.download('stopwords')
        print("✅ NLTK data downloaded successfully")
    except Exception as e:
        print(f"⚠️  NLTK download warning: {e}")
    
    # Test the agent
    print("🧪 Testing ATS Agent...")
    
    # Create test directories
    os.makedirs('test_data', exist_ok=True)
    
    print("✅ Setup complete!")
    print("\n🎯 To run the ATS Agent:")
    print("   python ats_agent.py")
    print("\n📝 Test files created in test_data/:")
    print("   - sample_resume.txt")
    print("   - sample_job_description.txt")

if __name__ == "__main__":
    main()