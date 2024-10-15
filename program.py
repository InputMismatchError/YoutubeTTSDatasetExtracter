import os
from pytubefix import YouTube
from pytubefix.cli import on_progress
import json
import csv
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import JSONFormatter
import subprocess
import re

def download_video(url):
    # Create a YouTube object
    yt = YouTube(url, on_progress_callback = on_progress)
    if yt.check_availability() == 'UNAVAILABLE':
        print('Video is unavailable')
        return
    else:
        print(f'Downloading video "{yt.title}"...')
    # Download the highest resolution video
    ys = yt.streams.get_audio_only()
    ys.download(output_path = f'results/{yt.title}', mp3=True)

    print(f'Video "{yt.title}" downloaded successfully!')

    return yt.title

def get_transcripts(video_id, languages):

    if YouTubeTranscriptApi.list_transcripts(video_id).find_manually_created_transcript(languages):
        print('Manually created transcript found on languaes: ', languages)
    elif YouTubeTranscriptApi.list_transcripts(video_id).find_generated_transcript(languages):
        print('Automatically Generated transcript found on languaes: ', languages)
        input('Automatically generated transcripts are possibly inaccurate. Would you like to continue? [y/n]: ')
        if input == 'n':
            sys.exit("Exiting...")
        else:
            print('Continuing...')
    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
    # Format the transcript as JSON
    formatter = JSONFormatter()
    json_formatted = formatter.format_transcript(transcript)
    json_formatted = json.loads(json_formatted)

    # Add the end time of each sentence
    for i in range(len(json_formatted)):
        json_formatted[i]['end'] = json_formatted[i]['start'] + json_formatted[i]['duration']

    return transcript,json_formatted

# Format the time in seconds to HH:MM:SS.mmm
def format_time(seconds, mode):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    milliseconds = int((seconds - int(seconds)) * 1000) if mode == "0" else int((seconds - int(seconds)) * 1000) + 1
    return f"{hours:02}:{minutes:02}:{int(seconds):02}.{milliseconds:03}"

def format_transcripts(json_transcripts):
    # Write to CSV
    with open(f'results/{video_name}/{video_name}_transcript.csv', 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        
        # Write header
        csv_writer.writerow(['start', 'end', 'text'])
        
        # Write rows
        for entry in json_transcripts:
            start_time = format_time(entry['start'],"0")
            end_time = format_time(entry['end'],"0")
            if start_time == end_time:
                end_time = format_time(entry['end'],"1")
            if entry['text'] == "[Müzik]":
                continue
            csv_writer.writerow([start_time, end_time, re.sub(r'[\n\t\r]', '', entry['text'])])

    print("CSV file created successfully.")

# Function to convert audio file to MP3 format
def convert_to_mp3(input_file, output_file):
    ffmpeg_command = [
        'ffmpeg', '-i', input_file,
        '-codec:a', 'libmp3lame', output_file
    ]
    subprocess.run(ffmpeg_command)
    # Convert the audio file to MP3

# Function to split the audio using ffmpeg and save as WAV
def split_audio(start, end, index):
    output_file = os.path.join(output_folder, f'clip_{index}.wav')  # Save as WAV
    ffmpeg_command = [
        'ffmpeg', '-i', converted_audio_file,
        '-ss', start, '-to', end,
        '-c', 'pcm_s16le', output_file  # Use PCM codec for WAV
    ]
    subprocess.run(ffmpeg_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # If you wish to see ffmpeg logs, comment out the next line and comment the line before 
    #subprocess.run(ffmpeg_command)

# Enter the URL of the video
video_name = download_video('https://www.youtube.com/watch?v=qFzKoemB7LY')

if not os.path.exists('results'):
    os.makedirs('results')

if not os.path.exists(f'results/{video_name}'):
    os.makedirs(f'results/{video_name}')


# Enter the video ID and expected transcript languages
transcripts = get_transcripts('qFzKoemB7LY', languages=['tr'])[1]
format_transcripts(transcripts)

# Define input/output paths
audio_file = f'results/{video_name}/{video_name}.mp3'
converted_audio_file = f'results/{video_name}/{video_name}_converted.mp3'
transcript_file = f'results/{video_name}/{video_name}_transcript.csv'  # Ensure this has the correct format
output_folder = f'results/{video_name}/output_clips'

# Convert the audio file to useable MP3 format
convert_to_mp3(audio_file, converted_audio_file)

# Create output folder if it doesn't exist
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Read the transcript CSV and process each segment
with open(transcript_file, 'r') as file:
    reader = csv.DictReader(file)
    clip_counter = 0
    for i, row in enumerate(reader):
        start_time = row['start']
        end_time = row['end']
        print(f'Splitting audio segment {i}: {start_time} to {end_time}')
        split_audio(start_time, end_time, i)  # Process each segment
        clip_counter += 1
        if clip_counter == 10:
            break

print("All clips have been created successfully.")