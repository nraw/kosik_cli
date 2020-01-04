import fire
import gkeepapi
import os
import json
import pickle
import requests
from bs4 import BeautifulSoup
from functools import lru_cache
from googletrans import Translator
from tabulate import tabulate


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
                selected_ids = [0]
                save_selection = False
            else:
                selected_ids, save_selection = get_selected_id(all_items_info)
            if selected_ids[0] == -1:
                link = get_product(product, tr, only_link=True)
                print(f'Find all {product} here: ')
                print(link)
                not_obvious_items[product] = link
                if save_selection:
                    new_save_items[product] = selected_ids
            else:
                selected_items[product] = []
                for selected_id in selected_ids:
                    selected_item = all_items_info[selected_id]
                    print(f'Selected {selected_item[1]}')
                    selected_items[product] += [selected_item[2]]
                selected_items[product] = '\n'.join(selected_items[product])
                if save_selection:
                    new_save_items[product] = selected_items[product]
    json.dump(selected_items, open('selected_items.json', 'w'))
    if not_obvious_items:
        print('++++++++++++++++++++++')
        print('Make sure you checked these items:')
        print(tabulate(not_obvious_items.items()))
    if selected_items:
        print('++++++++++++++++++++++')
        print('Go go go shopping:')
        print(tabulate(selected_items.items()))
    if new_save_items:
        update_saved_items(new_save_items)
        print(new_save_items)


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
        keep = gkeepapi.Keep()
        auth = pickle.load(open('credentials', 'rb'))  # assumes there is a pickle file 'credentials' that is a tuple with google username and pass
        keep.login(auth[0], auth[1])
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
        all_items_info = list(zip(range(len(all_items_names)), all_items_names, all_items_links))
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
        json.dump({}, open(saved_file, 'w'))
    saved_items = json.load(open(saved_file, 'r'))
    return saved_items


def update_saved_items(new_save_items, saved_file='saved_items.json'):
    saved_items = load_saved_items(saved_file)
    saved_items.update(new_save_items)
    json.dump(saved_items, open(saved_file, 'w'))


def get_selected_id(all_items_info):
    print(tabulate(all_items_info))
    selected_ids = input('Select item: ')
    if not selected_ids:
        selected_ids = '-1'
    save_selection = 's' in selected_ids  # Save item with s
    selected_ids = [int(s_id.replace('s', ''))
                    for s_id in selected_ids.split(',')]
    return selected_ids, save_selection


if __name__ == '__main__':
    fire.Fire(main)
