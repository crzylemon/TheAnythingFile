from theanythingfile import TheAnythingFile
taf = TheAnythingFile()
def testQuality(quality):
    img = taf.convertVideo("video.mp4", quality)
    # save image as result.tafi
    with open("video_qualities/" + str(quality) + ".tafv", "wb") as f:
        f.write(img)
    # now convert tafi back
    img2 = taf.tafvToMP4(img)
    # save it
    with open("video_qualities/" + str(quality) + ".mp4", "wb") as f:
        f.write(img2)
# test all qualities with increment of 10
for q in range(0, 101, 10):
    print("Testing quality:", q)
    testQuality(q)