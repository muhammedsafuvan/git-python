import sys
import os
import zlib
import hashlib 
from pathlib import Path

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

def hash_object(file, write=True):
    with open(file, 'rb') as f:
        content = f.read()

        header = f"blob {len(content)}\x00"
        store = header.encode("ascii") + content


        sha = hashlib.sha1(store).hexdigest()
        
        if write:
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


def write_tree(path: str):
    if os.path.isfile(path):
        return inspect_tree(path)
    
    contents = sorted(
        os.listdir(path),
        key=lambda x: x if os.path.isfile(os.path.join(path, x)) else f"{x}/",
    )
    s = ''
    for item in contents:
        if os.path.isfile(os.path.join(path, item)):
            s += f"100644 {item}\0".encode()
        else:
            s += f"40000 {item}\0".encode()

        sha1 = int.to_bytes(int(write_tree(os.path.join(path, item)), base=16), length=20, byteorder="big")
        s += sha1

    s = f"tree {len(s)}\0".encode() + s
    sha1 = hashlib.sha1(s).hexdigest()
    os.makedirs(f".git/objects/{sha1[:2]}", exist_ok=True)
    with open(f".git/objects/{sha1[:2]}/{sha1[2:]}", "wb") as f:
        f.write(zlib.compress(s))
    return sha1

def write_object(parent: Path, ty: str, content: bytes) -> str:
    content = ty.encode() + b" " + f"{len(content)}".encode() + b"\0" + content
    hash = hashlib.sha1(content, usedforsecurity=False).hexdigest()
    compressed_content = zlib.compress(content)
    pre = hash[:2]
    post = hash[2:]
    p = parent / ".git" / "objects" / pre / post
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(compressed_content)
    return hash
            
def commit_tree(tree_sha, commit_sha, message):
    contents = b"".join(
        [
            b"tree %b\n" % tree_sha.encode(),
            b"parent %b\n" % commit_sha.encode(),
            b"author ggzor <30713864+ggzor@users.noreply.github.com> 1714599041 -0600\n",
            b"committer ggzor <30713864+ggzor@users.noreply.github.com> 1714599041 -0600\n\n",
            message.encode(),
            b"\n",
        ]
    )
    hash = write_object(Path("."), "commit", contents)
    print(hash)




    

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

    elif command == "write-tree":
        paths = "./"
        write_tree(paths)

    elif command == "commit-tree":
        if sys.argv[3] == "-p":

            tree_sha = sys.argv[2]
            commit_sha = sys.argv[4]
            msg = sys.argv[6]
            commit_tree(tree_sha, commit_sha, msg)

    else:
        raise RuntimeError(f"Unknown command #{command}")


if __name__ == "__main__":
    main()
