from collections import defaultdict

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import json
import requests
import os.path

keywords = ["pop", "rock", "jazz", "metal", "blues", "country", "hip-hop", "rap", "classical", "EDM", "folk",
            "reggae", "punk", "R&B", "soul", "funk", "gospel", "world music", "experimental", "dubstep", "trap",
            "lofi", "folk", "disco", "indie", "dance", "swing", "anime", "kpop", "80s", "90s", "2000s", "2010s",
            "garage", "gospel", "grunge", "rainy-day", "acoustic", "spanish", "happy", "sad", "relaxing", "upbeat",
            "calming", "motivating", "soothing", "romantic", "energizing", "sentimental", "nostalgic", "melancholic",
            "inspiring", "passionate", "chill", "focus", "summer", "road-trip", "workout", "running", "yoga",
            "meditation", "studying", "concentration", "sleep", "party", "driving", "gaming", "cooking", "guitar",
            "piano", "drum"]

# The below aren't real
client_id = "z8za60nibjiyodz2xuv2fy9e8fycjyl3"
client_secret = "hr6q9f52zsejex4cu42or582Fl32"
client_credentials_manager = SpotifyClientCredentials(client_id=client_id,
                                                      client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)


# saves to the given directory the cover image(s) of the playlist in the dict as a .jpg file with the same name as
# its uri
def save_image_from_dict(pl_dict, directory="."):
    uri = plain_uri_from_dict(pl_dict)
    images = pl_dict["images"]
    image_url = images[0]['url']
    img_data = requests.get(image_url).content
    with open(f'{directory}/{uri}.jpg', 'wb') as handler:
        handler.write(img_data)


# saves to the given directory the json dump of the playlist in the dict as a .json file with the same name as its uri
def save_json_from_dict(pl_dict, directory="."):
    uri = plain_uri_from_dict(pl_dict)
    with open(f'{directory}/{uri}.json', 'w') as file:
        json.dump(pl_dict, file, indent=4)


# gets the plain string of the uri from the encoding of it in the playlist dictionary
def plain_uri_from_dict(pl_dict):
    ugly_uri = pl_dict["uri"]
    return ugly_uri.split(":")[-1]


# returns the set of strings of all lines from the given file, creating a new empty file if one does not exist
def load_set_from_file(file_name):
    if not os.path.isfile(file_name):
        open(file_name, 'a').close()
        return set()
    return set(line.strip() for line in open(file_name))


# creates a directory if it is not present
def create_dir_if_absent(dir_name):
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)


# Creates a json containing a prompt for each uri
def create_prompts(use_stripped=True, include_top_genre=True, include_top_artist=False):
    if not os.path.isfile("prompts.json"):
        open("prompts.json").close()

    with open("prompts.json", "r") as file:
        prompts = json.load(file)

    if not use_stripped:
        # create a json genre cache if file doesn't already exist (so we don't make repeated requests for artists)
        if not os.path.isfile("genre_cache.json"):
            open("genre_cache.json").close()

        with open("genre_cache.json", "r") as file:
            genre_cache = json.load(file)

    for filename in os.listdir("jsons"):
        # If we've already created a prompt for this uri
        uri = filename[:-5]
        if uri in prompts:
            continue

        # Get playlist json
        with open(f"jsons/{filename}", "r") as file:
            pl_dict = json.load(file)

        if not use_stripped:
            # Instead of iterating through each track, getting all the artists and adding their genres to a genre count,
            # we assume the most common artist's genre is representative of the playlist's most common genre.

            # Get most common artist (and their uri) in playlist by iterating through each track and counting the
            # artists
            artist_count = defaultdict(int)

            for track in pl_dict["tracks"]["items"]:
                # Track data can't be obtained (e.g. local file)
                if track["track"] is None:
                    continue

                artists = track["track"]["artists"]
                for artist in artists:
                    artist_name = artist["name"]
                    artist_uri = artist["uri"]
                    artist_count[(artist_name, artist_uri)] += 1

            # Get the artist with the highest count
            result = max(artist_count, key=artist_count.get, default=None)

            top_genre, top_artist = "", ""

            # If there are artists in the playlist we can get the top one
            if result is not None:
                top_artist, top_artist_uri = result
                genres = []
                # # Load genre cache each time
                # with open("genre_cache.json", "r") as file:
                #     genre_cache = json.load(file)
                if top_artist in genre_cache:
                    genres = genre_cache[top_artist]
                else:
                    if top_artist_uri is not None:
                        genres = sp.artist(top_artist_uri)["genres"]
                    genre_cache[top_artist] = genres
                    # # Save the genre cache to a json each time we add a new artist
                    # with open("genre_cache.json", 'w') as file:
                    #     json.dump(genre_cache, file, indent=4)

                # If genres are listed for the artist, get the first one. We're assuming first genre is the most common,
                # but we can try getting more later
                if len(genres) > 0:
                    top_genre = genres[0]

            print(top_artist)
            print(top_genre)

        prompt = pl_dict["name"] + " playlist cover image"

        print(prompt)

        if not use_stripped:
            if include_top_genre and top_genre != "":
                prompt += f", {top_genre}"
            if include_top_artist and top_artist != "":
                prompt += f", {top_artist}"

        # Add the uri and prompt to the dictionary
        uri = plain_uri_from_dict(pl_dict)
        prompts[uri] = prompt

    # Save the prompts to a json
    with open("prompts.json", "w") as file:
        json.dump(prompts, file, indent=4)

    if not use_stripped:
        # Save the genre cache to a json
        with open("genre_cache.json", 'w') as file:
            json.dump(genre_cache, file, indent=4)


def add_to_cache(cache, cache_name, value):
    with open(cache_name, "a") as file:
        file.write(f'{value}\n')
    cache.add(value)


class Scraper:
    # supports separate datasets through cache_info parameter.
    # keeps uris cached to avoid downloading the same playlist a bunch of times.
    def __init__(self, keywords=None, cache_info=None):
        self.keywords = keywords if keywords is not None else []
        self.cache_info = cache_info if cache_info is not None else {"keyword_set_file": "keyword_set",
                                                                     "uri_set_file": "uri_set", "image_dir": "images",
                                                                     "json_dir": "jsons"}
        self.uri_cache = load_set_from_file(self.cache_info["uri_set_file"])
        self.keyword_cache = load_set_from_file(self.cache_info["keyword_set_file"])
        self.image_dir = self.cache_info["image_dir"]
        self.json_dir = self.cache_info["json_dir"]
        create_dir_if_absent(self.image_dir)
        create_dir_if_absent(self.json_dir)

    def get_data_instance_from_uri(self, uri, playlist=None):
        # Check if playlist data has already been downloaded
        if uri in self.uri_cache:
            return

        if playlist is None:
            playlist = sp.playlist(uri)
        images = playlist["images"]
        num_images = len(images)

        # Playlist cover image is an autogenerated 2x2 grid, or it's a spotify official "seed" template,
        # or no cover image exists
        if num_images > 1 or (num_images > 0 and "seed" in images[0]["url"]) or num_images == 0:
            # Add to cache so that we don't do this check again
            add_to_cache(self.uri_cache, self.cache_info["uri_set_file"], uri)
            return

        # The below have many many edge cases (such as playlists not even existing or the album
        # cover of the first song not being available since it's a local file on the user's pc)

        # If number of distinct albums is less than or equal to 3 and the cover image equals the
        # album cover of the first song then skip
        # if len(set([track["album"]["uri"] for track in playlist["tracks"]["items"]])) <= 3 and \
        #         playlist["images"][0]["url"] == \
        #         playlist["tracks"]["items"][0]["track"]["album"]["images"][0]["url"]:
        #     continue

        # try:
        #     if playlist["images"][0]["height"] is not None and playlist["images"][0]["url"] == \
        #             playlist["tracks"]["items"][0]["track"]["album"]["images"][0]["url"]:
        #         return
        # except IndexError:
        #     return

        save_image_from_dict(playlist, directory=self.image_dir)
        save_json_from_dict(playlist, directory=self.json_dir)
        add_to_cache(self.uri_cache, self.cache_info["uri_set_file"], uri)

    # creates the dataset, saving/caching based on initialized values
    def create_data_set(self, wild_card=False, no_spotify=False, use_stripped=False):
        for keyword in self.keywords:
            # We don't want to do repeated searches for a keyword that has already been processed
            if keyword in self.keyword_cache:
                continue

            print(keyword)
            for offset in range(0, 1000, 50):
                if not wild_card:
                    playlists = sp.search(q=keyword, type='playlist', limit=50, offset=offset)['playlists']['items']
                else:
                    # TODO: Implement wild card search
                    pass

                for playlist in playlists:
                    if no_spotify and playlist["owner"]["id"] == "spotify":
                        continue

                    uri = plain_uri_from_dict(playlist)
                    if use_stripped:
                        self.get_data_instance_from_uri(uri, playlist=playlist)
                    else:
                        self.get_data_instance_from_uri(uri)

            # save the keyword to the keyword cache
            add_to_cache(self.keyword_cache, self.cache_info["keyword_set_file"], keyword)

        # TODO: Create JSON mapping uri to the keyword used to search so prompt generator can use it for genre


if __name__ == "__main__":
    # scraper = Scraper(keywords=keywords)
    # scraper.create_data_set(use_stripped=True)
    create_prompts()
