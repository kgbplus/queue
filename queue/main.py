#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  main.py
#  
#  Copyright 2016 Roman Mindlin <Roman@Mindlin.ru>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  
#      Raspberry Pi MAX7219 Driver 
#      
#      The MIT License (MIT)
#  
#  Copyright (c) 2016 Richard Hull
#  
#  Permission is hereby granted, free of charge, to any person obtaining a 
#  copy of this software and associated documentation files (the 
#  “Software”), to deal in the Software without restriction, including 
#  without limitation the rights to use, copy, modify, merge, publish, 
#  distribute, sublicense, and/or sell copies of the Software, and to 
#  permit persons to whom the Software is furnished to do so, subject to 
#  the following conditions:  
#  
#  The above copyright notice and this permission notice shall be included 
#  in all copies or substantial portions of the Software.  
#  
#  THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, 
#  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF 
#  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. 
#  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY 
#  CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, 
#  TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE 
#  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import sys
try:
	import max7219.led as led
	from time import sleep
	import urllib
	import urllib2
	import traceback
except ImportError as e:
    sys.stderr.write('Could not import submodules (exact error was: %s).' % e)
    
try:
    import RPi.GPIO as GPIO
except RuntimeError:
    print("Error importing RPi.GPIO!  This is probably because you need superuser privileges.  You can achieve this by using 'sudo' to run your script")

# Constants
BUT_START = 21   # Start button gpio number
BUT_END = 20   # End button gpio number
LED = 26   # Led gpio number

BOUNCE = 200   # Bounce time in ms

URL = "http://localhost"   # Queue server address
DEVICE_ID = 1   # Device's ID

class SegmentIndicator(object):
	"""
	7-segment led indicator
	
	Attributes
	"""
	
	def __init__(self):
		self.device = led.sevensegment(cascaded=1)
		self.device.brightness(7)
	
	def set(self,str):
		if len(str)>4:
			str = str[0:3]
		for _ in range(3):
			self.device.write_text(0, " " + str)
			sleep(.5)
			self.device.clear()
			sleep(.4)
		self.device.write_text(0, " " + str)
		
	def clear(self):
		self.device.clear()

class QueueServer(object):
	"""
	Queue Server object
	"""
	
	def __init__(self):
		pass
	
	def __comm(self, values):
		try:
			data = urllib.urlencode(values)
			req = urllib2.Request(URL, data)
			response = urllib2.urlopen(req)
		except Exception as e: 
			sys.stderr.write(traceback.format_exc())
			response = None

		return response
			
	def check(self):
		print("trying to receive id")
		ans = self._comm({'device_id' : DEVICE_ID, 'task' : 'req'})
		if ans != None:
			id = ans.read()
			self.__comm({'device_id' : DEVICE_ID, 'task' : 'ack', 'id' : id})
			return id
		else:
			return None
	
	def job_start(self,id):
		print("job start:id sent")
		ans = self.__comm({'device_id' : DEVICE_ID, 'task' : 'job_start', 'id' : id})
		if ans != None:
			if ans.read() == "OK":
				return True
		return False
	
	def job_end(self,id):
		print("job end:id sent")
		ans = self.__comm({'device_id' : DEVICE_ID, 'task' : 'job_end', 'id' : id})
		if ans != None:
			if ans.read() == "OK":
				return True
		return False
		
class LedIndicator(object):
	"""
	Led indicator
	"""
	
	def __init__(self):
		GPIO.setup(LED, GPIO.OUT, initial=GPIO.LOW)
	
	def on(self):
		GPIO.output(LED,GPIO.HIGH)
		
	def off(self):
		GPIO.output(LED,GPIO.LOW)
		
	def flash(self):
		self.off()
		sleep(.5)
		for _ in range(3):
			self.on()
			sleep(.5)
			self.off()
			sleep(.5)

class ButtonObject(object):
	"""
	Buttons
	"""
	
	def __init__(self):
		self.start_pressed = False
		self.end_pressed = False
		GPIO.setup(BUT_START, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
		GPIO.setup(BUT_END, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
		GPIO.add_event_detect(BUT_START, GPIO.RISING, callback = self.gpio_callback, bouncetime = BOUNCE)
		GPIO.add_event_detect(BUT_END, GPIO.RISING, callback = self.gpio_callback, bouncetime = BOUNCE)
		
	@property	
	def start_pressed(self):
		if self.start_pressed:
			self.start_pressed = False
			return True
		else:
			return False
	
	@property	
	def end_pressed(self):
		if self.end_pressed:
			self.end_pressed = False
			return True
		else:
			return False
		
	def gpio_callback(self,channel):
		if channel == BUT_START:
			self.start_pressed = True
		elif channel == BUT_END:
			self.end_pressed = True		
	
def main(args):
	try:
		#GPIO.cleanup()
		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False)
		
		indicator = SegmentIndicator()
		server = QueueServer()
		led = LedIndicator()
		but = ButtonObject()

		while True:
			id = server.check()
			if id == None:
				sleep(1) #check timeout
				continue
		
			indicator.set('{0:03d}'.format(id))
		
			while not but.start_pressed:
				sleep(.01)
			
			if server.job_start(id):
				led.on()
			else:
				led.flash()
				led.on()
			
			while not but.end_pressed:
				sleep(.01)
		
			if server.job_end(id):
				led.off()
			else:
				led.flash()
			
			indicator.clear()

	except KeyboardInterrupt:
		sys.stderr.write("\nCtrl-C pressed\n")
	
	except Exception as e: 
		sys.stderr.write(traceback.format_exc())
	
	finally:
		indicator.clear()
		GPIO.cleanup()
	return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
