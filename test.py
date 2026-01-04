from theanythingfile import TheAnythingFile
taf = TheAnythingFile()
def testQuality(quality):
    img = taf.convertImage("image.webp", quality)
    # save image as result.tafi
    with open("qualities/" + str(quality) + ".tafi", "wb") as f:
        f.write(img)
    # now convert tafi back
    img2 = taf.tafiToPNG(img)
    # save
    img2.save("qualities/" + str(quality) + ".png")
# test all qualities with increment of 10
for q in range(0, 101, 10):
    print("Testing quality:", q)
    testQuality(q)