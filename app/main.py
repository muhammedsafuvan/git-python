import struct
import sys
import os
from typing import Tuple, cast
import zlib
import hashlib 
from pathlib import Path
import urllib

def init(parent: Path):
    (parent / ".git").mkdir(parents=True)
    (parent / ".git" / "objects").mkdir(parents=True)
    (parent / ".git" / "refs").mkdir(parents=True)
    (parent / ".git" / "refs" / "heads").mkdir(parents=True)
    (parent / ".git" / "HEAD").write_text("ref: refs/heads/main\n")


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

def read_object(parent: Path, sha: str) -> Tuple[str, bytes]:
    pre = sha[:2]
    post = sha[2:]
    p = parent / ".git" / "objects" / pre / post
    bs = p.read_bytes()
    
    head, content = zlib.decompress(bs).split(b"\0", maxsplit=1)
    ty, _ = head.split(b" ")
    return ty.decode(), content

def clone(dir, url):
    parent = Path(dir)
    init(parent)
    # fetch refs
    req = urllib.request.Request(f"{url}/info/refs?service=git-upload-pack")
    with urllib.request.urlopen(req) as f:
        refs = {
            bs[1].decode(): bs[0].decode()
            for bs0 in cast(bytes, f.read()).split(b"\n")
            if (bs1 := bs0[4:])
            and not bs1.startswith(b"#")
            and (bs2 := bs1.split(b"\0")[0])
            and (bs := (bs2[4:] if bs2.endswith(b"HEAD") else bs2).split(b" "))
        }
    # render refs
    for name, sha in refs.items():
        Path(parent / ".git" / name).write_text(sha + "\n")
    # fetch pack
    body = (
        b"0011command=fetch0001000fno-progress"
        + b"".join(b"0032want " + ref.encode() + b"\n" for ref in refs.values())
        + b"0009done\n0000"
    )
    req = urllib.request.Request(
        f"{url}/git-upload-pack",
        data=body,
        headers={"Git-Protocol": "version=2"},
    )
    with urllib.request.urlopen(req) as f:
        pack_bytes = cast(bytes, f.read())
    pack_lines = []
    while pack_bytes:
        line_len = int(pack_bytes[:4], 16)
        if line_len == 0:
            break
        pack_lines.append(pack_bytes[4:line_len])
        pack_bytes = pack_bytes[line_len:]
    pack_file = b"".join(l[1:] for l in pack_lines[1:])
    def next_size_type(bs: bytes) -> Tuple[str, int, bytes]:
        ty = (bs[0] & 0b_0111_0000) >> 4
        match ty:
            case 1:
                ty = "commit"
            case 2:
                ty = "tree"
            case 3:
                ty = "blob"
            case 4:
                ty = "tag"
            case 6:
                ty = "ofs_delta"
            case 7:
                ty = "ref_delta"
            case _:
                ty = "unknown"
        size = bs[0] & 0b_0000_1111
        i = 1
        off = 4
        while bs[i - 1] & 0b_1000_0000:
            size += (bs[i] & 0b_0111_1111) << off
            off += 7
            i += 1
        return ty, size, bs[i:]
    def next_size(bs: bytes) -> Tuple[int, bytes]:
        size = bs[0] & 0b_0111_1111
        i = 1
        off = 7
        while bs[i - 1] & 0b_1000_0000:
            size += (bs[i] & 0b_0111_1111) << off
            off += 7
            i += 1
        return size, bs[i:]
    # get objs
    pack_file = pack_file[8:]  # strip header and version
    n_objs, *_ = struct.unpack("!I", pack_file[:4])
    pack_file = pack_file[4:]
    for _ in range(n_objs):
        ty, _, pack_file = next_size_type(pack_file)
        match ty:
            case "commit" | "tree" | "blob" | "tag":
                dec = zlib.decompressobj()
                content = dec.decompress(pack_file)
                pack_file = dec.unused_data
                write_object(parent, ty, content)
            case "ref_delta":
                obj = pack_file[:20].hex()
                pack_file = pack_file[20:]
                dec = zlib.decompressobj()
                content = dec.decompress(pack_file)
                pack_file = dec.unused_data
                target_content = b""
                base_ty, base_content = read_object(parent, obj)
                # base and output sizes
                _, content = next_size(content)
                _, content = next_size(content)
                while content:
                    is_copy = content[0] & 0b_1000_0000
                    if is_copy:
                        data_ptr = 1
                        offset = 0
                        size = 0
                        for i in range(0, 4):
                            if content[0] & (1 << i):
                                offset |= content[data_ptr] << (i * 8)
                                data_ptr += 1
                        for i in range(0, 3):
                            if content[0] & (1 << (4 + i)):
                                size |= content[data_ptr] << (i * 8)
                                data_ptr += 1
                        # do something with offset and size
                        content = content[data_ptr:]
                        target_content += base_content[offset : offset + size]
                    else:
                        size = content[0]
                        append = content[1 : size + 1]
                        content = content[size + 1 :]
                        # do something with append
                        target_content += append
                write_object(parent, base_ty, target_content)
            case _:
                raise RuntimeError("Not implemented")
    # render tree
    def render_tree(parent: Path, dir: Path, sha: str):
        dir.mkdir(parents=True, exist_ok=True)
        _, tree = read_object(parent, sha)
        while tree:
            mode, tree = tree.split(b" ", 1)
            name, tree = tree.split(b"\0", 1)
            sha = tree[:20].hex()
            tree = tree[20:]
            match mode:
                case b"40000":
                    render_tree(parent, dir / name.decode(), sha)
                case b"100644":
                    _, content = read_object(parent, sha)
                    Path(dir / name.decode()).write_bytes(content)
                case _:
                    raise RuntimeError("Not implemented")
    _, commit = read_object(parent, refs["HEAD"])
    tree_sha = commit[5 : 40 + 5].decode()
    render_tree(parent, parent, tree_sha)



    

def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!", file=sys.stderr)

    # Uncomment this block to pass the first stage
    #
    command = sys.argv[1]
    if command == "init":
        init(Path("."))
        print("Initialized git directory")

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

    elif command == "clone":
        dir = sys.argv[3]
        url = sys.argv[2]
        clone(dir, url)

    else:
        raise RuntimeError(f"Unknown command #{command}")


if __name__ == "__main__":
    main()
