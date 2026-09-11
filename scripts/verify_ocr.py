"""Verify the real local OCR engine against checked-in BDO-style panels."""
import os,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django;django.setup()
from guilds.modules.integrations import ocr,paired_scores
texts=[ocr((root/'fixtures'/'ocr'/name).read_bytes()) for name in ['war-names.png','war-scores.png']]
result=paired_scores(texts)
assert result==[{'name':'TestAlpha','kills':11,'deaths':2},{'name':'TestBeta','kills':7,'deaths':3}],result
print('Real Tesseract OCR passed on checked-in synthetic BDO-style paired panels.')
