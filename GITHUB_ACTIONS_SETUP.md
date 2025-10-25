# GitHub Actions Setup Instructions

Since the GitHub Actions workflow requires specific token permissions, here are the instructions to manually set up the automated podcast feed generation:

## Step 1: Create the Workflow File

Create a new file `.github/workflows/generate-podcast-feed.yml` in your repository with the following content:

```yaml
name: Generate Podcast Feed

on:
  push:
    branches: [ main ]
    paths:
      - 'audios/zhuoke/**'
  workflow_dispatch:

jobs:
  generate-feed:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v3
    
    - name: Install dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y exiftool file
        
    - name: Generate podcast feed
      run: |
        #!/bin/bash
        
        # Set paths relative to repository
        FEED_FILE="feed/kjck_podcast.xml"
        AUDIO_PATH="audios/zhuoke"
        FEED_TITLE="卓克-科技参考"
        AUTHOR="卓克"
        BASE_URL="https://raw.githubusercontent.com/${{ github.repository }}/main"
        
        # Initialize result variable
        result=""
        
        # Function to rename files (remove " - 得到APP" and spaces)
        rename_files(){
            cd "$AUDIO_PATH"
            # Loop through files with ' - 得到APP' pattern
            for file in *' - 得到APP'*; do
                if [ -f "$file" ]; then
                    # Remove ' - 得到APP' and spaces
                    newname=$(echo "$file" | sed 's/ - 得到APP//' | tr -d ' ')
                    mv "$file" "$newname"
                    echo "Renamed: $file -> $newname"
                fi
            done
            cd ../..
        }
        
        # Function to create RSS item entry
        make_entry() {
            local file="$1"
            local title=$(basename "$file" | sed 's/\.[^.]*$//')
            local fileduration=$(exiftool -S -Duration "$file" 2>/dev/null | sed 's/Duration: //' | sed 's/ (approx)//' || echo "00:00:00")
            local date=$(date -r "$file" '+%a, %d %b %Y %T %Z')
            local filesize=$(stat -c%s "$file")
            local mimetype=$(file -b --mime-type "$file")
            local fileurl="${BASE_URL}/${file}"
            
            result+="\n<item>"
            result+="\n\t<title>$title</title>"
            result+="\n\t<itunes:author>$AUTHOR</itunes:author>"
            result+="\n\t<pubDate>$date</pubDate>"
            result+="\n\t<enclosure url=\"$fileurl\" length=\"$filesize\" type=\"$mimetype\"/>"
            result+="\n\t<itunes:duration>$fileduration</itunes:duration>"
            result+="\n</item>"
        }
        
        # Function to write RSS header
        write_header() {
            result+="<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
            result+="\n<rss xmlns:itunes=\"http://www.itunes.com/dtds/podcast-1.0.dtd\" version=\"2.0\">"
            result+="\n<channel>"
            result+="\n<title>$FEED_TITLE</title>"
            result+="\n<itunes:author>$AUTHOR</itunes:author>"
            result+="\n<itunes:image href=\"https://piccdn3.umiwi.com/img/202011/03/202011032054372409251528.jpeg\" />"
            result+="\n<description>卓克科技参考播客</description>"
            result+="\n<language>zh-cn</language>"
            result+="\n<link>$BASE_URL</link>"
        }
        
        # Function to write RSS footer
        write_footer() {
            result+="\n</channel>"
            result+="\n</rss>"
        }
        
        # Main function to generate the feed
        generate_feed() {
            echo "Generating podcast feed..."
            echo "Audio path: $AUDIO_PATH"
            echo "Feed file: $FEED_FILE"
            
            # Write header
            write_header
            
            # Rename files if needed
            rename_files
            
            # Process each audio file
            cd "$AUDIO_PATH"
            for file in *.*; do
                if [ -f "$file" ]; then
                    echo "Processing: $file"
                    make_entry "$file"
                fi
            done
            cd ../..
            
            # Write footer
            write_footer
            
            # Write to feed file
            echo -e "$result" > "$FEED_FILE"
            echo "Feed generated successfully: $FEED_FILE"
        }
        
        # Run the feed generation
        generate_feed
        
    - name: Commit and push changes
      run: |
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        git add feed/kjck_podcast.xml
        git add audios/zhuoke/*  # Add any renamed files
        if git diff --staged --quiet; then
          echo "No changes to commit"
        else
          git commit -m "Auto-generate podcast feed"
          git push
        fi
```

## Step 2: Configure GitHub Token Permissions

To enable the workflow to push changes back to the repository, you need to:

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Create a new token with the following scopes:
   - `repo` (full control of private repositories)
   - `workflow` (update GitHub Action workflows)
3. Add the token as a repository secret:
   - Go to repository Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `PAT_TOKEN`
   - Value: Your personal access token

## Step 3: Update Workflow (Optional)

If you want to use the automatic token provided by GitHub instead of a personal access token, modify the workflow by adding this permission at the job level:

```yaml
jobs:
  generate-feed:
    runs-on: ubuntu-latest
    permissions:
      contents: write
```

## How It Works

1. **Trigger**: The workflow runs when:
   - Audio files are added/modified in `audios/zhuoke/` directory
   - Manually triggered via workflow_dispatch

2. **File Processing**: 
   - Renames files by removing " - 得到APP" and spaces
   - Extracts metadata (duration, size, mime type)
   - Generates proper RSS feed with iTunes podcast extensions

3. **Output**: Creates `feed/kjck_podcast.xml` with all podcast episodes

4. **Auto-commit**: Commits and pushes the generated feed back to the repository

## Manual Usage

You can also trigger the workflow manually:
1. Go to the repository's Actions tab
2. Select "Generate Podcast Feed" workflow
3. Click "Run workflow"
