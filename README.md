# swe-szn

### A Software Engineering Job Analyzer CLI

## Demo

_todo - terminal demo gif_

### Built With

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![OpenAI SDK](https://img.shields.io/badge/OpenAI-000000?style=for-the-badge&logo=openai&logoColor=white)
![Firecrawl SDK](https://img.shields.io/badge/🔥%20Firecrawl-fff?style=for-the-badge)

## Features

### Job Analysis

- **Web Scraping** - Automatically extract job posting content from URLs
- **Resume Parsing** - Parse PDF resumes and extract relevant information
- **AI-Powered Comparison** - Use OpenAI models to analyze job requirements vs your resume
- **Smart Caching** - Avoid re-processing with intelligent caching system

### Interactive Features

- **Rich Terminal UI** - Beautiful progress bars and formatted output
- **Interactive Chat** - Chat about analysis results with AI
- **Flexible Prompts** - Customizable analysis prompts for different scenarios

## Installation

### Build from Source

```bash
git clone https://github.com/yourusername/swe-szn.git
cd swe-szn
pip install -e .
```

### Prerequisites

- **Python 3.10+** - [Download here](https://www.python.org/downloads/)
- **OpenAI API Key** - [Get one here](https://platform.openai.com/api-keys)
- **Firecrawl API Key** - [Get one here](https://firecrawl.dev/)

## Quick Start

### 1. Configure API Keys
Create a `.env` file in the project root:

```bash
# Required
OPENAI_API_KEY=sk-your-key-here
FIRECRAWL_API_KEY=fc-your-key-here
# Optional
OPENAI_MODEL=gpt-4o-mini
SWE_SZN_CACHE_DIR=./cache
```

### 2. Run

```bash
swe-szn analyze-job path/to/your/resume.pdf https://example.com/job-posting
```

## Usage

### Basic Analysis

```bash
swe-szn analyze-job resume.pdf https://company.com/job
```

### Advanced Options

```bash
# Use different AI model
swe-szn analyze-job resume.pdf --model gpt-4

# Chat about the analysis
swe-szn analyze-job resume.pdf --chat

# Force re-run analysis (ignore cache)
swe-szn analyze-job resume.pdf --force
```

## Todo

- [x] Basic job analysis functionality
- [x] CLI interface
- [x] Configuration management
- [x] Export capabilities
- [ ] Interactive configuration setup
- [ ] Batch job analysis
- [ ] Advanced analytics dashboard
