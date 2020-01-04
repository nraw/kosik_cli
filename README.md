# Unofficial Kosik.cz cli

## What?

A way to find kosik.cz items for non-Czech speakers.

Takes the shopping list from your Google keep 'Shopping list' checkbox and iterates for each item by translating it into Czech and returning the available list of items.
Has the possibility of saving options.

## How?

Install everything necessary with
```
pip install -r requirements.txt
```

Run with
```
python3 kosik.py 
```
and add the corresponding flags if needed. 

For example to read from a raw txt file:
```
python3 kosik.py --list_file list_file.txt
```
Or to translate into czech:
```
python3 kosik.py --tr 1
```

If you want to access Google Keep, you need to have a note called `Shopping list` and add a pickle tuple with your credentials:

```
import pickle
pickle.dump((USERNAME, PASSWORD), open('credentials', 'wb'))
```

## Why?

Because I don't speak czech and I like doing stuff from the terminal.. :s

