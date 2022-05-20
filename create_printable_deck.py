
from typing import Tuple
import requests
import click
import progressbar

from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from os import walk, pardir, path
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import LEGAL
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Image
from math import ceil, floor
from os import mkdir, chdir


URL = 'https://scryfall.com/search?q='

successful_images = []
prog_bar = None

mutex = Lock()

@click.command()
@click.option('--card_path','-p', type=click.Path(exists=True), required=True)
@click.option('--deck_name','-d', type=click.Path(exists=False), required=True)
def main(card_path, deck_name):
    global prog_bar
    global mutex

    with open(card_path, 'r') as file:
        mkdir(deck_name)
        chdir(deck_name)
        cards_to_get = file.readlines()
        prog_bar = progressbar.ProgressBar(maxval=len(cards_to_get)*2)
    prog_bar.start()
    cards_to_get = map(str.strip, cards_to_get)

    with ThreadPoolExecutor() as executor:
        executor.map(get_images_for_card, cards_to_get)
    
    make_pdf(deck_name)
    mutex.acquire()
    prog_bar.finish()
    mutex.release()


def get_page(url) -> None:
    response = requests.get(url)
    return BeautifulSoup(response.text, 'html.parser')

def download_img_to_file(name, img_src):
    global successful_images
    global prog_bar
    global mutex

    sanitized_name = ''.join(name.split()).replace('.', '').replace(',', '')

    img_response = requests.get(img_src)

    if not img_response:
        print(f'could not get img_response for {name}')
        return

    with open(sanitized_name+'.jpg', 'wb') as jpg:
        jpg.write(img_response.content)

    successful_images.append(sanitized_name+'.jpg')
    
    mutex.acquire()
    prog_bar.update(prog_bar.currval+1)
    mutex.release()

def get_img_src(name, class_name):
    soup = get_page(URL+f'"{name}"')
    card_image_div = soup.find('div', {'class', class_name})
    if not card_image_div:
        cards = soup.findAll('a', {'class', 'card-grid-item-card'})
        for card in cards:
            if card.find('span', {'class', 'card-grid-item-invisible-label'}).get_text().lower() == name.lower():
                soup = get_page(card['href'])
                card_image_div = soup.find('div', {'class', class_name})
    if not card_image_div:
        if "front" in class_name:
            print(f'could not find card_image_div for {name}')
        return None
    img_sec = card_image_div.find('img')
    if not img_sec:
        print(f'could not find img_sec for {name}')
        return None
    img_src = img_sec.attrs['src']

    if not img_src:
        print(f'could not find img_src for {name}:{class_name}')
        return None
    return img_src

def get_image_front(name):
    return get_img_src(name, 'card-image-front')
def get_image_back(name):
    return get_img_src(name, 'card-image-back')

def get_images_for_card(name):
    front_src = get_image_front(name)
    back_src = get_image_back(name)
    if back_src is not None:
        download_img_to_file(name+"_back", back_src)
    if front_src is not None:
        download_img_to_file(name, front_src)
    else:
        print(f'could not find img for {name}')
    
def make_pdf(deck_name):
    global successful_images
    global prog_bar
    global mutex
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
        
        # To explain:
        # Downloading the images is 50% of the work because our "max" is 2* number of images, 
        # therefore we need to figure out how much of the overall "max" value our pages take up
        # we do this by taking half the max value i.e., 50% and then adding the ammount equivalent to
        # half of the percentage of the pages we are done with  
        mutex.acquire()
        additional_percent = (current_page/num_pages)/2
        new_value = floor((prog_bar.maxval/2)+(additional_percent*prog_bar.maxval))
        prog_bar.update(new_value)
        mutex.release()
        c.showPage()
    c.save()
        


if __name__ == "__main__":
    main()