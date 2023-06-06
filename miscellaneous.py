import json
import math
import os
import shutil
import numpy as np


def metadata_builder():
    f = open("prompts.json")
    data = json.load(f)
    f.close()

    for thing in data:
        with open("images/metadata.jsonl", "a", encoding="utf-8") as myfile:
            string = "{" + f'"file_name": {json.dumps(thing + ".jpg")}, "text": {json.dumps(data[thing])}' + "}"
            myfile.write(f'{string}\n')


def merge_json_files(file_paths, output_file_path):
    merged_json = {}
    for file_path in file_paths:
        with open(file_path, 'r') as file:
            json_data = json.load(file)
        merged_json.update(json_data)

    with open(output_file_path, 'w') as output_file:
        json.dump(merged_json, output_file, indent=4)


def find_unique_files(folder1, folder2, output_folder):
    # Create the output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Get the list of files in both folders
    files1 = set(os.listdir(folder1))
    files2 = set(os.listdir(folder2))

    # Find files that are unique to each folder
    unique_files = files1.symmetric_difference(files2)

    # Copy unique files to the output folder
    for file in unique_files:
        source = None
        if file in files1:
            source = os.path.join(folder1, file)
        elif file in files2:
            source = os.path.join(folder2, file)

        if source:
            destination = os.path.join(output_folder, file)
            shutil.copy2(source, destination)
            print(f"Copied {file} to {output_folder}")


def rename_images(folder_path):
    # Get the list of files in the folder
    files = os.listdir(folder_path)

    # Iterate over the files in the folder
    for file_name in files:
        if file_name.endswith("_0.jpg"):
            # Extract the base name without "_0.jpg"
            base_name = file_name[:-6]

            # Check if a file without "_0" exists
            if base_name + ".jpg" in files:
                # Construct the path for the file to delete
                file_to_delete = os.path.join(folder_path, file_name)

                # Delete the file
                os.remove(file_to_delete)
                print(f"Deleted {file_name}")
            else:
                # Replace "_0" with an empty string in the file name
                new_file_name = file_name.replace("_0", "")

                # Construct the paths for the old and new file names
                old_file_path = os.path.join(folder_path, file_name)
                new_file_path = os.path.join(folder_path, new_file_name)

                # Rename the file
                os.rename(old_file_path, new_file_path)
                print(f"Renamed {file_name} to {new_file_name}")


def remove_duplicates(folder_path):
    # Get a list of all files in the folder
    file_list = os.listdir(folder_path)

    # Traverse the file list and collect file names and paths
    for file_name in file_list:
        if "(1)" in file_name:
            file_path = os.path.join(folder_path, file_name)
            print(f"Deleting '{file_path}'...")
            os.remove(file_path)


# create an 80-10-10 train-val-test split on images
# images_path is the path of the folder containing the images
def split_data(images_path):
    files = np.array(os.listdir(images_path))

    # shuffle data and split into the train, val, and test sets
    permutations = np.random.permutation(len(files))
    train_files = files[permutations[:math.ceil(len(files) * 0.8)]]
    val_files = files[permutations[math.ceil(len(files) * 0.8):int(len(files) * 0.9)]]
    test_files = files[permutations[math.ceil(len(files) * 0.9):]]

    # Create the train, val, and test folders if they don't exist
    new_dataset_path = "dataset"
    if not os.path.exists(new_dataset_path):
        os.makedirs(new_dataset_path)
    train_folder = os.path.join(new_dataset_path, "train")
    val_folder = os.path.join(new_dataset_path, "val")
    test_folder = os.path.join(new_dataset_path, "test")
    if not os.path.exists(train_folder):
        os.makedirs(train_folder)
    if not os.path.exists(val_folder):
        os.makedirs(val_folder)
    if not os.path.exists(test_folder):
        os.makedirs(test_folder)

    # Create a text file including the names of the files in each set
    with open("train.txt", "w") as file:
        for file_name in train_files:
            file.write(file_name + "\n")
    with open(os.path.join("val.txt"), "w") as file:
        for file_name in val_files:
            file.write(file_name + "\n")
    with open(os.path.join("test.txt"), "w") as file:
        for file_name in test_files:
            file.write(file_name + "\n")

    # Copy the files to the train, val, and test folders
    for file_name in train_files:
        shutil.copy2(os.path.join(images_path, file_name), train_folder)
    for file_name in val_files:
        shutil.copy2(os.path.join(images_path, file_name), val_folder)
    for file_name in test_files:
        shutil.copy2(os.path.join(images_path, file_name), test_folder)

    return train_files, val_files


def create_test_set_prompts_json_from_metadata():
    with open("images/metadata.jsonl", "r") as file:
        data = {}
        for line in file:
            json_line = json.loads(line)
            data[json_line["file_name"]] = json_line["text"]

    # create a list of train and val files from the train.txt and val.txt files
    test_files = []
    with open("test.txt", "r") as file:
        for line in file:
            test_files.append(line.strip())
    prompts = {}
    for file_name in data:
        if file_name in test_files:
            prompts[file_name[:-4]] = data[file_name]

    with open("test_set_prompts.json", 'w') as file:
        json.dump(prompts, file, indent=4)


if __name__ == "__main__":
    split_data("images")
    create_test_set_prompts_json_from_metadata()
