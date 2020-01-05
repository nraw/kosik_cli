import fire
import gkeepapi
import os
import json
import pickle
import requests
import os
from bs4 import BeautifulSoup
from functools import lru_cache
from googletrans import Translator
from tabulate import tabulate
from dotenv import load_dotenv


def main(tr=None, lucky=None, avoid_list=None, info=None, list_file=None):
    """ Main function that takes the shopping list and iterates through items
    
    Keyword Arguments:
        tr {boolean} -- whether to translate the text from english to czech
        lucky {boolean} -- feeling lucky = gives first product instead of list
        avoid_list {boolean} -- avoids saved items even if they are saved
        info {str} -- which info to retrieve: link, name, link&name (default)
        list_file {str} -- path to a file that contains 1 product per row, 
            if empty, will use google keep's shopping list
    """
    shopping_list = get_shopping_list(list_file)
    selected_items = {}
    new_save_items = {}
    not_obvious_items = {}
    for product in shopping_list:
        print(f'Finding {product}')
        link = get_product(product, tr, only_link=True)
        print(link)
        all_items_info = get_product(product, tr, lucky, avoid_list, info)
        # TODO: handle saved -1s
        if type(all_items_info) == str:  # saved item
            selected_items[product] = all_items_info
            print(f'Already saved product: {all_items_info}')
        else:
            if lucky:
                selected_ids = ['0']
                save_selection = False
            else:
                selected_ids, save_selection = get_selected_id(all_items_info)
            selected_item, not_obvious_item, new_save_item = handle_selected_ids(product, selected_ids, save_selection, all_items_info, tr)
            if selected_item:
                selected_items[product] = selected_item
            if not_obvious_item:
                not_obvious_items[product] = not_obvious_item
            if new_save_item:
                new_save_items[product] = new_save_item
    json.dump(selected_items, open('selected_items.json', 'w'))
    if not_obvious_items:
        print('++++++++++++++++++++++')
        print('Make sure you checked these items:')
        print(tabulate(not_obvious_items.items()))
    if selected_items:
        print('++++++++++++++++++++++')
        print('Shopping list:')
        print(tabulate(selected_items.items()))
    if new_save_items:
        update_saved_items(new_save_items)
        print(new_save_items)
    to_cart = input('Add items to cart (Y/n):')
    if to_cart.lower() != 'n':
        put_selected_items_in_shopping_cart()


def handle_selected_ids(product, selected_ids, save_selection, all_items_info, tr):
    new_save_item = None
    if selected_ids[0] == '-1':
        selected_item = None
        link = get_product(product, tr, only_link=True)
        print(f'Find all {product} here: ')
        print(link)
        not_obvious_item = link
        if save_selection:
            new_save_item = selected_ids
    else:
        not_obvious_item = None
        selected_item_list = []
        for selected_id in selected_ids:
            if ':' in selected_id:
                selected_id, quantity = (int(num) for num in selected_id.split(':'))
            else:
                selected_id = int(selected_id)
                quantity = 1
            selected_item_info = all_items_info[selected_id]
            print(f'Selected {selected_item_info[1]}')
            selected_item_list += [selected_item_info[4]]
        selected_item = '\n'.join(selected_item_list)
        if save_selection:
            new_save_item = selected_item
    return selected_item, not_obvious_item, new_save_item


def get_shopping_list(list_file=None):
    """retrieves the shopping list either from google keep or from a file
    
    Keyword Arguments:
        list_file {str} -- shopping list file
    
    Returns:
        shopping_list {[str]} -- list of strings
    """
    if list_file:  # if list provided load list, else load google keep
        with open('list_file.txt') as f:
            shopping_list_raw = f.readlines()
        shopping_list = [product.strip() for product in shopping_list_raw]
    else:
        load_dotenv()
        if 'GOOGLE_USER' not in os.environ or 'GOOGLE_PASS' not in os.environ:
            raise Exception("GOOGLE_USER or GOOGLE_PASS not environment variables. Add them to `.env` file or your system envs.")
        keep = gkeepapi.Keep()
        keep.login(os.environ['GOOGLE_USER'], os.environ['GOOGLE_PASS'])
        shopping_list_objects = list(keep.find('Shopping'))[0].unchecked
        shopping_list = [product.text for product in shopping_list_objects]
    return shopping_list


def get_product(product, tr=None, lucky=None, avoid_list=None, info=None, only_link=None):
    saved_items = load_saved_items()
    if product in saved_items and avoid_list is None:  # if we saved the item, return it
        return saved_items[product]
    if tr:  # translation?
        product = translate(product)
    if only_link:  # don't look for the item and return just the link to browse
        url = f'https://www.kosik.cz/vyhledavani?search={product}'
        return url
    all_items = get_all_items(product)
    if lucky:  # return the first item
        if all_items:
            all_items = [all_items[0]]
    if info == 'link':
        all_items_info = [texto.parent.get('href') for texto in all_items]
    elif info == 'name':
        all_items_info = [texto.text.strip() for texto in all_items]
    else:
        all_items_names = [texto.text.strip() for texto in all_items]
        all_items_links = [texto.parent.get('href') for texto in all_items]
        all_items_prices = [item.parent.parent.find('span', {'class': 'price__actual-price'}).get('content') for item in all_items]
        all_items_id = [texto.parent.parent.parent.get('data-product-id') for texto in all_items]
        all_items_info = list(zip(
            range(len(all_items_names)), 
            all_items_names, 
            all_items_prices, 
            all_items_links, 
            all_items_id
        ))
    return all_items_info


@lru_cache(1000)
def translate(word, src='en', dest='cs'):
    tr = Translator()
    translation = tr.translate(word, src=src, dest=dest).text
    return translation


@lru_cache(100)
def get_all_items(product):
    url = f'https://www.kosik.cz/vyhledavani?search={product}'
    res = requests.get(url)
    bs = BeautifulSoup(res.text, features='lxml')
    all_items = bs.find_all('h3')
    return all_items


def load_saved_items(saved_file='saved_items.json'):
    if not saved_file in os.listdir():
        with open(saved_file, 'w') as f:
            saved_items = {}
            json.dump(saved_items, f)
    else:
        with open(saved_file, 'r') as f:
            saved_items = json.load(f)
    return saved_items


def update_saved_items(new_save_items, saved_file='saved_items.json'):
    saved_items = load_saved_items(saved_file)
    saved_items.update(new_save_items)
    with open(saved_file, 'w') as f:
        json.dump(saved_items, f)


def get_selected_id(all_items_info):
    print(tabulate(all_items_info))
    selected_ids = input('Select item: ')
    if not selected_ids:
        selected_ids = '-1'
    save_selection = 's' in selected_ids  # Save item with s
    selected_ids = [s_id.replace('s', '')
                    for s_id in selected_ids.split(',')]
    return selected_ids, save_selection


def put_selected_items_in_shopping_cart(selected_file = 'selected_items.json'):
    selected_items = json.load(open(selected_file, 'r'))
    payload, headers = get_payload_and_headers()
    session = requests.Session()
    session.post('https://www.kosik.cz/', data=payload, headers=headers)
    for item, item_ids in selected_items.items():
        for item_id in item_ids.split('\n'):
            payload2 = dict(productId=item_id, quantity='1')  # TODO: quantity
            rh = session.post('https://www.kosik.cz/kosik/set-to-cart', data=payload2, headers=headers)
            if rh.ok:
                print(f'Added {item} to cart ({item_id})')
            else:
                print(f'Problem with {item} ({item_id})')


def get_payload_and_headers():
    load_dotenv()
    if 'KOSIK_USER' not in os.environ or 'KOSIK_PASS' not in os.environ:
        raise Exception("KOSIK_USER or KOSIK_PASS not environment variables. Add them to `.env` file or your system envs.")
    payload = {
        'username': os.environ['KOSIK_USER'],
        'password': os.environ['KOSIK_PASS'],
        'projectDomainId': '6',
        'do': 'signInForm-submit',
        'send': 'Přihlásit se'
        }
    headers = {'User-Agent': 'Mozilla/5.0'}
    return payload, headers


if __name__ == '__main__':
    fire.Fire(main)
