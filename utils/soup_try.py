from bs4 import BeautifulSoup

html_doc = """<p>Přeji všem čtenářům tohoto blogu, i těm náhodným :), příjemné prožití Vánočních svátků :).</p>
<p>A tady přidávám mnou vysněného Santu ;-).</p>
<p><a href="../../soubory/sexy-christmas-babe-girl-lingerie-photoshoot.jpg"><img style="vertical-align: baseline;" src="../../soubory/sexy-christmas-babe-girl-lingerie-photoshoot.jpg" alt="Ta je, co? ;-)" width="300" height="380" /></a><a href="/files/progit2-cz/" target="_self">/soubory/progit2-cz/</a
</p>"""

soup = BeautifulSoup(html_doc, 'html.parser')
for tag in soup.find_all():
    if 'src' in tag.attrs:
        if 'soubory' in tag['src']:
            index = tag['src'].index('soubory') + 7 # end of soubory
            tag['src'] = f"/files{tag['src'][index:]}"
    if 'href' in tag.attrs:
        if 'soubory' in tag['href']:
            index = tag['href'].index('soubory') + 7 # end of soubory
            tag['href'] = f"/files{tag['href'][index:]}"


print(soup)
