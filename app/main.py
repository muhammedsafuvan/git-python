import sys
import os
import zlib
import hashlib 

def init():
    os.mkdir(".git")
    os.mkdir(".git/objects")
    os.mkdir(".git/refs")
    with open(".git/HEAD", "w") as f:
        f.write("ref: refs/heads/main\n")
    print("Initialized git directory")

def cat_file(sha):
    path = f"./.git/objects/{sha[:2]}/{sha[2:]}"
    with open(path, 'rb') as f:  # Open the file in binary mode
        content = zlib.decompress(f.read())  # Read and decompress the binary data
        # print(content)
        null_byte_index = content.find(b'\x00')
        if null_byte_index == -1:
            raise ValueError("Invalid Git object: null byte not found")
        
        # Slice the content to extract the message
        message = content[null_byte_index + 1:].strip(b"\n")
        print(message.decode('utf-8'), end="")

def hash_object(file):
    with open(file, 'rb') as f:
        content = f.read()

        header = f"blob {len(content)}\x00"
        store = header.encode("ascii") + content


        sha = hashlib.sha1(store).hexdigest()
        git_path = os.path.join(os.getcwd(), ".git/objects")
        os.mkdir(os.path.join(git_path, sha[0:2]))
        with open(os.path.join(git_path, sha[0:2], sha[2:]), "wb") as file:
            file.write(zlib.compress(store))

        print(sha, end="")

        
def inspect_tree(sha: str):
    path = f"./.git/objects/{sha[:2]}/{sha[2:]}"
    with open(path, 'rb') as f:  # Open the file in binary mode
        content = zlib.decompress(f.read())  #
        content_str = content.decode('utf-8', errors='ignore')  # Decode with UTF-8 and ignore errors if any.

        # Split by null character to isolate entries
        entries = content_str.split('\0')

        # Extract names from each entry
        names = []
        for entry in entries:
            if ' ' in entry:  # Check if there is a space indicating mode and name
                parts = entry.split(' ')
                if len(parts) > 1 and parts[0] != 'tree':
                    name = parts[-1]  # Name is the last part of the split
                    names.append(name)

        for name in names:
            print(name)



    

def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!", file=sys.stderr)

    # Uncomment this block to pass the first stage
    #
    command = sys.argv[1]
    if command == "init":
        init()

    elif command == "cat-file":
        sha = sys.argv[3]
        cat_file(sha)

    elif command == "hash-object":
        if len(sys.argv) != 4:
            exit()
        
        file = sys.argv[3]
        hash_object(file)

    elif command == "ls-tree" and sys.argv[2] == "--name-only":
        sha = sys.argv[3]
        inspect_tree(sha)

    

    else:
        raise RuntimeError(f"Unknown command #{command}")


if __name__ == "__main__":
    main()
