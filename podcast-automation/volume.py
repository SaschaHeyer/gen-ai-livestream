import numpy as np
from pydub import AudioSegment
from scipy.io import wavfile
import noisereduce as nr

def adjust_and_reduce_noise(input_file, target_dBFS, output_file, prop_decrease=0.8, n_std_thresh=2.0):
    # Load the audio file
    audio = AudioSegment.from_file(input_file)
    
    # Adjust volume
    change_in_dBFS = target_dBFS - audio.dBFS
    adjusted_audio = audio.apply_gain(change_in_dBFS)
    
    # Convert to raw data for noise reduction
    samples = np.array(adjusted_audio.get_array_of_samples())
    
    # Noise profile (e.g., first 1 second)
    noise_sample = samples[:audio.frame_rate]
    
    # Reduce noise with fine-tuned parameters
    reduced_noise = nr.reduce_noise(
        y=samples, 
        sr=adjusted_audio.frame_rate, 
        y_noise=noise_sample, 
        prop_decrease=prop_decrease,
        n_std_thresh_stationary=n_std_thresh
    )
    
    # Convert back to AudioSegment
    reduced_audio = AudioSegment(
        reduced_noise.tobytes(), 
        frame_rate=adjusted_audio.frame_rate,
        sample_width=adjusted_audio.sample_width,
        channels=adjusted_audio.channels
    )
    
    # Export the cleaned audio
    reduced_audio.export(output_file, format="mp3")
    print(f"Volume adjusted and noise reduced for {input_file}. Saved to {output_file}")

# Example usage with fine-tuning
adjust_and_reduce_noise(
    "audio-files/15_Ieva.mp3", 
    -15.0, 
    "audio-files/ieva_cleaned.mp3",
    prop_decrease=0.9,  # Reduce noise less aggressively
    n_std_thresh=2.5   # Increase threshold for noise detection
)
