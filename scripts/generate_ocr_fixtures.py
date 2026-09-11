"""Generate deterministic BDO-style paired score panels for OCR regression checks."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'fixtures'/'ocr'
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def panel(header,rows,path):
    image=Image.new('RGB',(900,360),'#111820');draw=ImageDraw.Draw(image)
    draw.rectangle((18,18,882,342),fill='#18232d',outline='#9d8650',width=3)
    draw.rectangle((28,28,872,92),fill='#242d35');draw.text((52,40),header,font=ImageFont.truetype(FONT,34),fill='#d6bd78')
    font=ImageFont.truetype(FONT,44)
    for index,row in enumerate(rows):
        y=116+index*92;draw.line((40,y-12,860,y-12),fill='#3b4650',width=2);draw.text((58,y),row,font=font,fill='#f1eee7')
    image.save(path,optimize=True)

OUTPUT.mkdir(parents=True,exist_ok=True)
panel('Family Name',['TestAlpha','TestBeta'],OUTPUT/'war-names.png')
panel('Kills        Deaths',['11                 2','7                   3'],OUTPUT/'war-scores.png')
