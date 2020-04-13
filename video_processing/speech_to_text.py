import time
import azure.cognitiveservices.speech as speechsdk

# Creates an instance of a speech config with specified subscription key and service region.
# Replace with your own subscription key and region identifier from here: https://aka.ms/speech/sdkregion
speech_key, service_region = "d215959e99c24caeb2ee4e620016782f", "westus"
speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
speech_config.request_word_level_timestamps()

# Creates an audio configuration that points to an audio file.
# Replace with your own audio filename.
def speech_to_text(audio_filename, output_filename=None):
    if not output_filename:
        output_filename = audio_filename.split('.')[0]+f'_text.json'

    data = list()
    done = False

    audio_input = speechsdk.audio.AudioConfig(filename=audio_filename)
    # Creates a recognizer with the given settings
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)

    print("Recognizing first result...")

    def stop_cb(evt):
        """callback that signals to stop continuous recognition upon receiving an event `evt`"""
        print('CLOSING on {}'.format(evt))
        nonlocal done
        done = True

    # Connect callbacks to the events fired by the speech recognizer
    def store_text(evt):
        nonlocal data
        f = open(output_filename, 'w')
        f.write(evt.result.json)
        f.close()

    speech_recognizer.recognizing.connect(lambda evt: print('RECOGNIZING: {}'.format(evt.result.json)))
    speech_recognizer.recognized.connect(store_text)#lambda evt: print('RECOGNIZED: {}'.format(evt.result.json)))
    speech_recognizer.session_started.connect(lambda evt: print('SESSION STARTED: {}'.format(evt)))
    speech_recognizer.session_stopped.connect(lambda evt: print('SESSION STOPPED {}'.format(evt)))
    speech_recognizer.canceled.connect(lambda evt: print('CANCELED {}'.format(evt)))
    # stop continuous recognition on either session stopped or canceled events
    speech_recognizer.session_stopped.connect(stop_cb)
    speech_recognizer.canceled.connect(stop_cb)

    # Start continuous speech recognition
    speech_recognizer.start_continuous_recognition()
    while not done:
        time.sleep(.5)

    speech_recognizer.stop_continuous_recognition()

if __name__=='__main__':
    audio_filenames = ["whatstheweatherlike.wav", "whatstheweatherlike.wav"]#, "file.wav"]
    for i, audio_filename in enumerate(audio_filenames):

        output_filename = audio_filename.split('.')[0]+f'_text{i}.json'
        speech_to_text(audio_filename, output_filename)
