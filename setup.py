from setuptools import setup, find_packages

setup(
    name="agentic_assistant",
    version="0.1.0",
    description="Assistant with specialized agents and tool capabilities",
    author="Arthur B",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        # Core dependencies
        "openai>=1.0.0",  # For LLM API interaction
        "requests>=2.25.0",  # For HTTP requests
        
        # Web extraction dependencies
        "playwright>=1.30.0",  # For advanced web extraction
        "beautifulsoup4>=4.9.0",  # For fallback web extraction
        
        # Optional but recommended
        "tqdm>=4.60.0",  # For progress bars
        "colorama>=0.4.4",  # For colored terminal output
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "agentic-assistant=agentic_assistant.assistant:main",
        ],
    },
)