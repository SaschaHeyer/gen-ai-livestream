from google.cloud import texttospeech_v1beta1


# Instantiates a client
client = texttospeech_v1beta1.TextToSpeechClient()

multi_speaker_markup = texttospeech_v1beta1.MultiSpeakerMarkup()

turn1 = texttospeech_v1beta1.MultiSpeakerMarkup.Turn()
turn1.text = "I've heard that the Google Cloud multi-speaker audio generation sounds amazing!"
turn1.speaker = "S"
multi_speaker_markup.turns.append(turn1)

turn2 = texttospeech_v1beta1.MultiSpeakerMarkup.Turn()
turn2.text = "Oh? What's so good about it?"
turn2.speaker = "R"
multi_speaker_markup.turns.append(turn2)

turn3 = texttospeech_v1beta1.MultiSpeakerMarkup.Turn()
turn3.text = "Well.."
turn3.speaker = "S"
multi_speaker_markup.turns.append(turn3)

turn4 = texttospeech_v1beta1.MultiSpeakerMarkup.Turn()
turn4.text = "Well what?"
turn4.speaker = "R"
multi_speaker_markup.turns.append(turn4)

turn5 = texttospeech_v1beta1.MultiSpeakerMarkup.Turn()
turn5.text = "Well, you should find it out by yourself!"
turn5.speaker = "S"
multi_speaker_markup.turns.append(turn5)

turn6 = texttospeech_v1beta1.MultiSpeakerMarkup.Turn()
turn6.text = "Alright alright, let's try it out!"
turn6.speaker = "R"
multi_speaker_markup.turns.append(turn6)

# Set the text input to be synthesized
synthesis_input = texttospeech_v1beta1.SynthesisInput(multi_speaker_markup=multi_speaker_markup)

# Build the voice request, select the language code ('en-US') and the ssml
# voice gender ('neutral')
voice = texttospeech_v1beta1.VoiceSelectionParams(
    language_code="en-US", name="en-US-Studio-MultiSpeaker"
)

# Select the type of audio file you want returned
audio_config = texttospeech_v1beta1.AudioConfig(
    audio_encoding=texttospeech_v1beta1.AudioEncoding.MP3
)

# Perform the text-to-speech request on the text input with the selected
# voice parameters and audio file type
response = client.synthesize_speech(
    input=synthesis_input, voice=voice, audio_config=audio_config
)

# The response's audio_content is binary.
with open("output.mp3", "wb") as out:
  # Write the response to the output file.
  out.write(response.audio_content)
  print('Audio content written to file "output.mp3"')