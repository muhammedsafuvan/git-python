import sys
import os
import zlib


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!", file=sys.stderr)

    # Uncomment this block to pass the first stage
    #
    command = sys.argv[1]
    if command == "init":
        os.mkdir(".git")
        os.mkdir(".git/objects")
        os.mkdir(".git/refs")
        with open(".git/HEAD", "w") as f:
            f.write("ref: refs/heads/main\n")
        print("Initialized git directory")
    elif command == "cat-file":
        sha = sys.argv[3]
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

    

    else:
        raise RuntimeError(f"Unknown command #{command}")


if __name__ == "__main__":
    main()
