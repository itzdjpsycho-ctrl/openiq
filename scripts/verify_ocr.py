"""Generate a synthetic panel and verify the real local OCR engine."""
import os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django;django.setup()
from PIL import Image,ImageDraw,ImageFont
from guilds.modules.integrations import ocr,paired_scores
from io import BytesIO
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',36)
texts=[]
for name,content in [('names','Aster\nJuniper'),('scores','42        7\n14        5')]:
    image=Image.new('RGB',(480,160),'white');ImageDraw.Draw(image).multiline_text((20,20),content,font=font,fill='black',spacing=10)
    stream=BytesIO();image.save(stream,format='PNG');texts.append(ocr(stream.getvalue()))
result=paired_scores(texts)
assert result==[{'name':'Aster','kills':42,'deaths':7},{'name':'Juniper','kills':14,'deaths':5}],result
print('Real Tesseract OCR passed on generated paired-panel fixture.')
