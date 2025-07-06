# GraTeX Discord Bot

Discord bot for generating LaTeX formula graphs using GraTeX.

## Features

- Generate mathematical graphs from LaTeX formulas
- Interactive zoom and label size controls
- Real-time graph manipulation with Discord reactions

## Deployment on Railway

### Prerequisites

1. Discord bot token
2. Railway account

### Setup Instructions

1. **Clone or upload this repository to Railway**

2. **Set environment variables in Railway:**
   - `TOKEN`: Your Discord bot token

3. **Deploy:**
   Railway will automatically:
   - Install Python dependencies from `requirements.txt`
   - Set up Chrome and ChromeDriver via buildpacks
   - Start the bot using the command in `Procfile`

### Environment Variables

- `TOKEN`: Discord bot token (required)

### Commands

- `!gratex "latex_formula"`: Generate a graph from LaTeX formula
- `!gratex help`: Show help message

### Example Usage

```
!gratex "\cos x\le\cos y"
```

### Interactive Controls

After generating a graph, you can use reactions to:
- 2⃣3⃣4⃣6⃣: Change label size
- 🔎: Zoom in
- 🔭: Zoom out
- ✅: Complete editing
- 🚮: Delete message

## Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your bot token
   ```

3. Run the bot:
   ```bash
   python main.py
   ```

## Troubleshooting

### Common Issues on Railway

1. **ChromeDriver not found error:**
   - Railway automatically installs Chromium and ChromeDriver via nixpacks.toml
   - Check the Railway logs for WebDriver initialization messages

2. **WebDriver timeout errors:**
   - The bot retries WebDriver creation with multiple fallback methods
   - Check if the GraTeX website is accessible

3. **Memory issues:**
   - Railway free tier has memory limits
   - The bot is configured with minimal Chrome arguments to reduce memory usage

### Deployment Notes

- Uses nixpacks.toml for proper Chrome/ChromeDriver installation
- Includes multiple fallback mechanisms for WebDriver creation
- Automatically detects Chrome binary location in Railway environment
- Includes comprehensive error handling and logging

## Technical Details

- Uses Selenium WebDriver to interact with GraTeX web interface
- Generates PNG images from LaTeX formulas
- Supports various label sizes and zoom levels
- Built for Railway deployment with proper buildpack configuration