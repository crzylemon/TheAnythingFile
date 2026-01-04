# The Anything File

__version__ = "0.1.0"

from . import *
import struct
import zlib
import PIL.Image as Image
import cv2
import numpy as np
import os

MAGIC = b'TAF!'
VERSION = 1
# Type, Flag, 4 bytes of length
CHUNK = "<BBI"
# TYPES:
#0x01  Text (UTF‑8)
#0x02  Raw bytes (anything)
#0x03  Image (Custom Format)
#0x04  Video (Custom format)
#0x05  Animated image (custom frames)
#0x06  Project (folders, files, nested stuff)
#0x07  Audio
# FLAGS:
#Bit 1: Compressed?
#Bit 2: Hidden?
#Bit 3: Encrypted?


class TheAnythingFile:
    def __init__(self):
        self.chunks = []
    def convertImage(self, image, quality=95, show_progress=False):
        # Path or content?
        if isinstance(image, str):
            img = Image.open(image)
        else:
            img = image
        img = img.convert("RGBA")
        width, height = img.size
        MAGICIMG = b'TAFI'
        IMGVERSION = 1
        # Magic, Version, Width, Height, 0
        IMGHEADER = struct.pack("<4sIII", MAGICIMG, IMGVERSION, width, height)
        # Fast compression using brightness sum for complexity estimation
        pixels = []
        
        for y in range(height):
            if show_progress and y % (height // 10) == 0:
                pixel_progress = (y / height) * 100
                print(f"  Processing pixels: {pixel_progress:.0f}%")
            for x in range(width):
                r, g, b, a = img.getpixel((x, y))
                
                # Use brightness sum as simple complexity measure
                brightness = r + g + b
                
                # High brightness areas tend to have more detail
                if brightness > 400:  # Bright areas - preserve more
                    bits_to_remove = min(7, max(0, (100 - quality) * 5 // 100))
                else:  # Darker areas - can compress more
                    bits_to_remove = min(7, max(0, (100 - quality) * 7 // 100))
                
                if quality >= 90:
                    # High quality - minimal or no compression
                    pass
                elif bits_to_remove > 0:
                    # Convert to YUV for luminance-chrominance separation
                    luma = int(0.299 * r + 0.587 * g + 0.114 * b)  # Luminance (brightness)
                    u = int(-0.169 * r - 0.331 * g + 0.5 * b + 128)  # Chrominance
                    v = int(0.5 * r - 0.419 * g - 0.081 * b + 128)  # Chrominance
                    
                    # Preserve luminance more than chrominance
                    luma_bits = max(0, bits_to_remove - 2)  # Preserve brightness
                    chroma_bits = min(7, bits_to_remove + 1)  # Compress color more
                    
                    if luma_bits > 0:
                        luma = (luma >> luma_bits) << luma_bits
                    if chroma_bits > 0:
                        u = (u >> chroma_bits) << chroma_bits
                        v = (v >> chroma_bits) << chroma_bits
                    
                    # Convert back to RGB
                    r = max(0, min(255, int(luma + 1.402 * (v - 128))))
                    g = max(0, min(255, int(luma - 0.344 * (u - 128) - 0.714 * (v - 128))))
                    b = max(0, min(255, int(luma + 1.772 * (u - 128))))
                
                pixels.append((r, g, b, a))
        
        # Simple compression without RLE to avoid shifting issues
        compressed = bytearray()
        for r, g, b, a in pixels:
            compressed.extend([r, g, b, a])
        
        data = bytearray()
        data.extend(IMGHEADER)
        data.extend(struct.pack("<I", len(compressed)))
        data.extend(compressed)
        
        return data
    def tafiToPNG(self, data):
        # Read header
        MAGICIMG, IMGVERSION, width, height = struct.unpack("<4sIII", data[:16])
        if MAGICIMG != b'TAFI':
            raise ValueError("Invalid TAFI image data")
        
        # Read compressed data
        compressed_size = struct.unpack("<I", data[16:20])[0]
        compressed_data = data[20:20+compressed_size]
        
        # Simple decompression - read pixels directly
        pixels = []
        for i in range(0, len(compressed_data), 4):
            if i + 3 < len(compressed_data):
                r, g, b, a = compressed_data[i:i+4]
                pixels.append((r, g, b, a))
        
        img = Image.new("RGBA", (width, height))
        img.putdata(pixels[:width*height])
        return img
    def convertVideo(self, video, quality=95):
        print(f"Starting video conversion with quality={quality}")
        # Path or content?
        if isinstance(video, str):
            print(f"Opening video file: {video}")
            vid = open(video, "rb")
        else:
            vid = video
        MAGICVID = b'TAFV'
        VIDVERSION = 1
        # Magic, Version
        VIDHEADER = struct.pack("<4sI", MAGICVID, VIDVERSION)
        data = bytearray()
        data.extend(VIDHEADER)
        # Find video frames and convert each frame to TAFI.
        cap = cv2.VideoCapture(video if isinstance(video, str) else video.name)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        print(f"Video info: {frame_count} frames at {fps} FPS")
        
        # Add FPS and frame count to header
        data.extend(struct.pack("<fI", fps, frame_count))
        
        frame_num = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_num += 1
            progress = (frame_num / frame_count) * 100
            print(f"Processing frame {frame_num}/{frame_count} ({progress:.1f}%)")
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            frame_data = self.convertImage(img, quality, show_progress=True)
            #TEMPORARY: Save to image
            img2 = self.tafiToPNG(frame_data)
            img2.save(f"debug_frame_{frame_num}.png")
            print(f"Frame {frame_num} compressed to {len(frame_data)} bytes")
            data.extend(struct.pack("<I", len(frame_data)))
            data.extend(frame_data)
        
        cap.release()
        print(f"Video conversion complete. Total size: {len(data)} bytes")

        return data
    def tafvToMP4(self, data):
        MAGICVID, VIDVERSION = struct.unpack("<4sI", data[:8])
        if MAGICVID != b'TAFV':
            raise ValueError("Invalid TAFV video data")
        offset = 8
        fps, frame_count = struct.unpack("<fI", data[offset:offset+8])
        offset += 8
        frames = []
        for _ in range(frame_count):
            frame_size = struct.unpack("<I", data[offset:offset+4])[0]
            offset += 4
            frame_data = data[offset:offset+frame_size]
            offset += frame_size
            png = self.tafiToPNG(frame_data)
            frames.append(png)
            # TEMPORARY DEBUG - Save image
            png.save(f"debug_frame_{_}.png")
        
        # Create video from frames with better settings
        if not frames:
            raise ValueError("No frames found")
            
        height, width = frames[0].size
        output_path = '/tmp/output.mp4'
        
        # Use AVI format which is more reliable
        output_path = '/tmp/output.avi'
        
        # Use MJPG codec which is most compatible
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        
        # Ensure dimensions are even numbers (required by some codecs)
        if width % 2 != 0:
            width += 1
        if height % 2 != 0:
            height += 1
            
        video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        if not video_writer.isOpened():
            raise RuntimeError("Could not create video writer")
        
        print(f"Creating video with {len(frames)} frames at {fps} FPS, size {width}x{height}")
        
        for i, frame in enumerate(frames):
            print(f"Writing frame {i+1}/{len(frames)}")
            # Convert RGBA to RGB
            frame_rgb = frame.convert('RGB')
            
            # Resize frame if dimensions were adjusted
            if frame_rgb.size != (width, height):
                frame_rgb = frame_rgb.resize((width, height), Image.LANCZOS)
            
            frame_array = np.array(frame_rgb, dtype=np.uint8)
            
            # Convert RGB to BGR for OpenCV
            frame_bgr = cv2.cvtColor(frame_array, cv2.COLOR_RGB2BGR)
            
            video_writer.write(frame_bgr)
        
        video_writer.release()
        
        # Check if file was created
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Video file was not created at {output_path}")
        
        # Read the video file as bytes
        with open(output_path, 'rb') as f:
            video_bytes = f.read()

        # Remove output file
        os.remove(output_path)

        
        return video_bytes 

