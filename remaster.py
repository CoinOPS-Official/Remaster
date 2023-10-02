# pip install pydub pyloudnorm soundfile mutagen numpy scipy imageio_ffmpeg
import os
import tempfile
import numpy as np
import scipy.io.wavfile
import mutagen
import soundfile as sf
import pyloudnorm as pyln

from subprocess import Popen, PIPE
from pydub import AudioSegment
from textwrap import wrap

from imageio_ffmpeg import get_ffmpeg_exe
import tempfile
import shutil
import concurrent.futures

import warnings
warnings.filterwarnings("ignore")


MEDIA_TAG = 'Remastered by: Team CoinOPS'


def encrypt(text):
    """ secret tag encryptor """
    code = ''.join(bin(ord(x))[2:].zfill(8) for x in text)
    code = code.replace('0',' ')
    code = code.replace('1','\t')
    return code
    
def decrypt(code):
    """ secret tag decryptor """
    code = code.replace(' ',  '0')
    code = code.replace('\t', '1')
    return ''.join([chr(int(x, 2)) for x in wrap(code, 8)])


class Media(object):
    def __init__(self, infile):
        self.fname     = infile # full path to asset
        self.asset     = os.path.split(self.fname)[-1] # asset name (eg: 1942.mp4)
        self.buffer    = tempfile.TemporaryDirectory()
        self.wav       = os.path.join(self.buffer.name, 'remaster.wav')
        self.mp3       = os.path.join(self.buffer.name, 'remaster.mp3')
        self.meter     = None # the stored pyloudnorm meter
        self.rate      = None # the source audio rate
        self.data      = None # the source audio data
        self.norm      = None # the normalized audio
        self.dB        = -60
        
        
        # extract audio to buffer
        try:
            self.data, self.rate = sf.read(self.fname)

        # extract audio from video
        except:
            try:
                asg = AudioSegment.from_file(self.fname)
                dtype = getattr(np, "int{:d}".format(asg.sample_width * 8))
                self.data = np.ndarray((int(asg.frame_count()), asg.channels), buffer=asg.raw_data, dtype=dtype)
                self.rate = asg.frame_rate
                scipy.io.wavfile.write(self.wav, self.rate, self.data)
                self.data, self.rate = sf.read(self.wav)

            # media has no audio
            except:
                pass
            
            
        # get current loudness
        if self.data is not None:
            self.meter = pyln.Meter(self.rate)
            self.dB = self.meter.integrated_loudness(self.data)              


    def __del__(self):
        self.buffer.cleanup()
        
    
    def remaster(self, outfile=None, target_db=-24, tag=MEDIA_TAG):
        """ export media with normalized audio """
        
        # if no export file name given, extrapolate
        if not outfile:
            folder = os.path.split(self.fname)[0]
            outfile  = os.path.join(folder, str(target_db) + 'dB', 'media', self.asset)
            
        # if folder doesn't exist
        folder, _ = os.path.split(outfile)
        if not os.path.isdir(folder):
            os.makedirs(folder)        
        

        # if there is no audio, just copy source file
        if self.data is None:
            shutil.copyfile(self.fname, outfile)
        
        # there is audio, normalize and remux    
        elif self.dB is not None:
            normalized = pyln.normalize.loudness(self.data, self.dB, target_db)
            scipy.io.wavfile.write(self.wav, self.rate, normalized)
            
            # Remux with ffmpeg
            cmd = fr'"{get_ffmpeg_exe()}" -y -i "{self.wav}" -vn -ar 44100 -ac 2 -b:a 192k "{self.mp3}"'
            Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE).communicate()
            
            cmd = fr'"{get_ffmpeg_exe()}" -y -i "{self.fname}" -i "{self.mp3}" -c copy -map 0:v:0 -map 1:a:0 "{outfile}"'
            Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE).communicate()

            # apply media tag if any
            if tag is not None:
                try: 
                    obj = mutagen.File(outfile)
                    obj.delete()
                    obj.tags['info']=MEDIA_TAG
                    obj.save()
                except:
                    pass
                
        return outfile
                
            
            
    def difference(self, target_db=-24, rounded=False):
        """ returns the difference loudness in dB """
        difference = 0.0
        
        if self.data is not None:

            difference = np.diff([self.dB, target_db])[0]
            if self.dB < target_db:
                difference *= -1
                
        if rounded:
            try:
                return round(difference)
            except:
                return 0
        
        return difference
    
    
    
    def mame_ini(self, outfile=None, target_db=-24, tag=MEDIA_TAG):
        """ writes mame .ini file with secret tag """
        
        # if no export file name given, extrapolate
        if not outfile:
            folder = os.path.split(self.fname)[0]
            asset  = os.path.splitext(self.asset)[0] + '.ini'
            outfile  = os.path.join(folder, str(target_db) + 'dB', 'ini', asset)
            
        level = self.difference(target_db=target_db, rounded=True)
        text = f'volume {level}\n'
        if tag:
            text += f'{encrypt(tag)}\n'
    
        folder, _ = os.path.split(outfile)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        
        with open(outfile, 'w') as io:
            io.write(text)
            
        return outfile
    
    

      
def batch_remaster(path, target_db=-24):
    """ remasters all media found to the target loudness (default = -24dB) """
    
    def threaded_remaster(fname, target_db=-24):
        media = Media(fname)
        return media.remaster(target_db=target_db)

    # find all the files to process
    media_files = []
    target_volumes = []
    for root, dirs, files in os.walk(path):
        for f in files:
            if os.path.splitext(f)[-1].lower() in ['.avi', '.mp4']:
                f = os.path.join(root, f)
                media_files.append(f)
                target_volumes.append(target_db)

    
    # remaster!
    print (f'Remastering {len(media_files)} files...')
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for fname in executor.map(threaded_remaster, media_files, target_volumes):
            if fname:
                print(fname)
                
    print ('All Done!')
                
       
                
def batch_mame_ini(path, target_db=-24):
    """ generates mame.ini files from given reference footage """
    
    def threaded_remaster(fname, target_db=-24):
        media = Media(fname)
        return media.mame_ini(target_db=target_db)

    # find all the files to process
    media_files = []
    target_volumes = []
    for root, dirs, files in os.walk(path):
        for f in files:
            if os.path.splitext(f)[-1].lower() in ['.avi', '.mp4', '.wav', '.mp3']:
                f = os.path.join(root, f)
                media_files.append(f)
                target_volumes.append(target_db)

    
    # remaster!
    print (f'Generating {len(media_files)} ini files...')
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for fname in executor.map(threaded_remaster, media_files, target_volumes):
            if fname:
                print(fname)
                
    print ('All Done!')


