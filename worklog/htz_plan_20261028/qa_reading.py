from pathlib import Path
import pypdfium2 as pdf
from PIL import Image,ImageOps,ImageDraw
base=Path(__file__).parent
for pattern,tag in [('*预算*.pdf','annual'),('*提纲*.pdf','literature')]:
    src=next(base.glob(pattern)); doc=pdf.PdfDocument(str(src)); out=base/('qa_'+tag);out.mkdir(exist_ok=True)
    thumbs=[]
    for i,page in enumerate(doc):
        im=page.render(scale=1.3).to_pil().convert('RGB');im.save(out/f'page-{i+1}.png')
        print(tag,i+1,page.get_textpage().get_text_range()[:75].replace('\r\n',' / '))
        im.thumbnail((560,800)); tile=Image.new('RGB',(580,835),'#dddddd');tile.paste(im,((580-im.width)//2,25));ImageDraw.Draw(tile).text((12,5),f'{tag} {i+1}',fill='black');thumbs.append(tile)
    for j in range(0,len(thumbs),4):
        group=thumbs[j:j+4];sheet=Image.new('RGB',(1160,835*((len(group)+1)//2)),'white')
        for k,im in enumerate(group):sheet.paste(im,((k%2)*580,(k//2)*835))
        sheet.save(out/f'contact-{j//4+1}.png')
