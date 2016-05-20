#!/usr/bin/env python

import datetime
import os
import signal
import time
import threading

from pygame import camera, image
from pytz import timezone

IMAGE_DIR = './webcam_images'
VIDEO_DIR = './videos'
IMAGE_SIZE = (1280, 1024)
TIMEZONESTRING = 'Europe/Amsterdam'
SLEEPSEC = 30
UPLOAD_VIDEO = False

class Recorder(object):

    def __init__(self, image_dir=None, image_size=None, timezonestring=None, 
            sleepsec=None):
        self.count = 0
        self.img_dir = image_dir
        self.image_size = image_size
        self.tzstring = timezonestring
        self.sleepsec = sleepsec
        self.running = False
        self.camera = None
        self.first_image = True
        self.init_count()
        self.init_camera()

    def init_count(self):
        files = os.listdir(self.img_dir)
        if len(files) == 0:
            count = 0
            self.first_image = True
        else:
            latest = sorted(files)[-1]
            count = int(latest.split('.')[0].split('_')[-1])
            count += 1
            self.first_image = True
        self.count = count

    def init_camera(self):
        camera.init()
        self.camera = camera.Camera(camera.list_cameras()[0], self.image_size)
        self.camera.start()

    def take_image(self):
        fname = '%s/image_%05i.bmp' % (self.img_dir, self.count)
        img = self.camera.get_image()
        image.save(img, fname)
        oname = self.annotate_image(fname)
        return oname

    def record(self):
        if self.first_image:
            oname = self.take_image()
            oname = self.take_image()
            self.first_image = False
        else:
            oname = self.take_image()
        self.count += 1
        print("Got image: %s" % oname)

    def annotate_image(self, fname):
        localtz = timezone(self.tzstring)
        oname = fname[:-3] + 'jpg'
        stat = os.stat(fname)
        dt = datetime.datetime.fromtimestamp(stat.st_ctime, localtz)
        annotation = dt.strftime('%Y-%m-%d %H:%M %z')
        cmd = ('montage -label "%s" %s -geometry +0+0 '
                    '-background Khaki -pointsize 18 %s') % (annotation, fname, 
                            oname)
        os.system(cmd)
        if os.path.exists(fname) and os.path.exists(oname):
            os.unlink(fname)
        return oname

    def start(self):
        self.running = True
        while self.running:
            self.record()
            time.sleep(self.sleepsec)

    def stop(self):
        self.running = False
        self.cleanup()

    def cleanup(self):
        self.camera.stop()

class TimeLapse(object):

    def __init__(self, image_dir=None, image_size=None, timezonestring=None, 
            sleepsec=None, video_dir=None):
        self.img_dir = image_dir
        self.vid_dir = video_dir
        self.recorder_data = {
                'image_dir': image_dir,
                'image_size': image_size,
                'timezonestring': timezonestring,
                'sleepsec': sleepsec
                }

    def start(self):
        self.recorder = Recorder(**self.recorder_data)
        self.thread = threading.Thread(target=self.recorder.start)
        self.thread.start()
        print("Started recorder")

    def stop(self):
        self.recorder.stop()
        self.thread.join()
        print("Stopped recorder")

    def make_video(self, start_time):
        print("Making video")
        self.videofile = '%s/%s_timelapse.mp4' % (self.vid_dir, 
                start_time.strftime('%Y%m%d'))
        os.system("ffmpeg -f image2 -r 20 -i %s/image_%%05d.jpg -sameq %s" % 
                (self.img_dir, self.videofile))
        self.videotitle = 'Timelapse for %s' % (
                start_time.strftime('%A %B %d, %Y'))

    def upload_video(self):
        print("Uploading video")
        os.system(("python ./youtube_upload.py --file='%s' --title='%s' "
            "--privacyStatus='private' --description=''") % (self.videofile, 
                self.videotitle))

    def cleanup(self):
        print("Cleaning up")
        files = os.listdir(self.img_dir)
        for f in files:
            fpath = self.img_dir + os.sep + f
            os.remove(fpath)

def sigterm_hdl(signal, frame):
    raise SystemExit

def main():
    signal.signal(signal.SIGTERM, sigterm_hdl)
    try:
        while True:
            now = datetime.datetime.now()
            tomorrow = now + datetime.timedelta(days=1)
            stop_time = tomorrow.replace(hour=2, minute=0, second=0, 
                    microsecond=0)
            wait_secs = (stop_time - now).seconds

            tl = TimeLapse(image_dir=IMAGE_DIR, image_size=IMAGE_SIZE, 
                    timezonestring=TIMEZONESTRING, sleepsec=SLEEPSEC, 
                    video_dir=VIDEO_DIR)
            tl.start()
            time.sleep(wait_secs)
            tl.stop()
            tl.make_video(now)
            if UPLOAD_VIDEO:
                tl.upload_video()
            tl.cleanup()
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        tl.stop()

if __name__ == '__main__':
    main()
