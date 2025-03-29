# Installation Guide

This guide provides detailed instructions for setting up the Agentic Assistant system.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git (for cloning the repository)
- SearxNG instance (either local or remote)

## Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/agentic_assistant.git
cd agentic_assistant
```

## Step 2: Install the Package

### Option 1: Install in Development Mode

```bash
pip install -e .
```

This installs the package in development mode, allowing you to modify the code and see changes without reinstalling.

### Option 2: Install as Regular Package

```bash
pip install .
```

## Step 3: Install Playwright

The webpage reader tool requires Playwright:

```bash
pip install playwright
playwright install firefox
```

## Step 4: Configure SearxNG

You need a SearxNG instance for the web search functionality.

### Option A: Use a Public Instance

You can use a public SearxNG instance. Update the `SEARXNG_URL` in your config.py.

### Option B: Set Up a Local Instance

Follow these steps to set up a local SearxNG instance using Docker:

```bash
# Pull the SearxNG Docker image
docker pull searxng/searxng

# Run SearxNG on port 8080
docker run -d -p 8080:8080 --name searxng searxng/searxng
```

## Step 5: Configure the System

1. Copy the example configuration file:

```bash
cp example.config.py agentic_assistant/config.py
```

2. Edit the configuration file with your settings:

```bash
# Open with your preferred editor
nano agentic_assistant/config.py
```

Update the following settings:

- `SEARXNG_URL`: URL of your SearxNG instance
- LLM API settings (URL, API key, model name)
- Any other settings you wish to customize

## Step 6: Verify Installation

Run the interactive console to verify everything is working:

```bash
python run.py
```

You should see the Agentic Assistant console interface start up.

## Troubleshooting

### SearxNG Issues

If SearxNG is not working:

1. Check if the SearxNG instance is running:
   ```bash
   curl http://localhost:8080/healthz
   ```

2. If using Docker, check container status:
   ```bash
   docker ps -a | grep searxng
   ```

### LLM API Issues

If you're having issues with the LLM API:

1. Verify your API key is correct
2. Check that the API URL is accessible from your machine
3. Ensure the model name is valid for your provider

### Webpage Reader Issues

If the webpage reader isn't working:

1. Verify Playwright is installed:
   ```bash
   playwright --version
   ```

2. Make sure Firefox was installed:
   ```bash
   playwright install firefox --check
   ```

## Getting Help

If you encounter issues not covered here, please:

1. Check the [GitHub issues](https://github.com/yourusername/agentic_assistant/issues)
2. Create a new issue with details about your problem
