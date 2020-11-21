
import requests
import click

from os import walk, pardir
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import LEGAL
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Image
from math import ceil
from os import mkdir, chdir


URL = 'https://scryfall.com/search?q='

successful_images = []

@click.command()
@click.option('--card_path','-p', type=click.Path(exists=True), required=True)
@click.option('--deck_name','-d', type=click.Path(exists=False), required=True)
def main(card_path, deck_name):
    with open(card_path, 'r') as file:
        mkdir(deck_name)
        chdir(deck_name)
        for line in file.readlines():
            #print(f'Getting img for {line}')
            line = line.strip()
            if line:
                get_img(line)
    
    make_pdf(card_path, deck_name)


def get_page(url):
    response = requests.get(url)
    return BeautifulSoup(response.text, 'html.parser')

def get_img(name):
    global successful_images
    
    soup = get_page(URL+f'"{name}"')
    card_image_div = soup.find('div', {'class', 'card-image-front'})
    if not card_image_div:
        cards = soup.findAll('a', {'class', 'card-grid-item-card'})
        for card in cards:
            if card.find('span', {'class', 'card-grid-item-invisible-label'}).get_text().lower() == name.lower():
                soup = get_page(card['href'])
                card_image_div = soup.find('div', {'class', 'card-image-front'})
    
    img_sec = card_image_div.find('img')
    img_src = img_sec.attrs['src']

    sanitized_name = ''.join(name.split()).replace('.', '').replace(',', '')

    if not img_src:
        print(f'could not find img_src for {name}')
        return

    img_response = requests.get(img_src)

    if not img_response:
        print(f'could not get img_response for {name}')
        return

    with open(sanitized_name+'.jpg', 'wb') as jpg:
        jpg.write(img_response.content)

    successful_images.append(sanitized_name+'.jpg')

def make_pdf(path, deck_name):

    c = Canvas(f'{deck_name}.pdf', pagesize=LEGAL)
    num_pages =  ceil(len(successful_images)/9)
    if num_pages <= 0:
        num_pages = 1

    for current_page in range(num_pages):
        if current_page != num_pages:
            num_items = len(successful_images[(current_page * 9) : ((current_page+1)*9)])
        else:
            num_items = len(successful_images[current_page * 9:])
        for i in range(num_items):
            if i in [0,3,6]:
                x_align = 0.25
            elif i in [1,4,7]:
                x_align = 3
            else:
                x_align = 5.75
            if i in [0, 1, 2]:
                y_align = 0.25
            elif i in [3,4,5]:
                y_align = 4
            else:
                y_align = 7.75
            img_name = successful_images[i+(current_page*9)]
            c.drawImage(img_name, x_align*inch, y_align*inch, width=2.5*inch, height=3.48*inch)
        c.showPage()
    c.save()
        


if __name__ == "__main__":
    main()