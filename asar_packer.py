"""Minimal ASAR reader/writer: replace files in-place, rebuild header offsets."""
import struct, json, io, os, sys

class Asar:
    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            head = f.read(16)
        self.header_pickle_size = struct.unpack('<I', head[4:8])[0]
        self.data_start = 8 + self.header_pickle_size
        # head layout: [0]=4, [1]=header_len, [2]=json_len+4, [3]=json_len
        # JSON starts at byte 16 and ends exactly at data_start.
        string_len = struct.unpack('<I', head[12:16])[0]
        with open(path, 'rb') as f:
            f.seek(16)
            self.header = json.loads(f.read(string_len).decode('utf-8', 'ignore'))
        self.string_len = string_len

    def _walk(self, parts, node):
        for part in parts:
            node = node['files'][part] if 'files' in node else node[part]
        return node

    def read(self, path):
        node = self._walk([x for x in path.split('/') if x], self.header['files'])
        with open(self.path, 'rb') as f:
            f.seek(self.data_start + int(node['offset']))
            return f.read(int(node['size']))

    def list(self, path=''):
        node = self._walk([x for x in path.split('/') if x], self.header['files']) if path else self.header['files']
        return sorted(node.get('files', node).keys())

    def replace_and_write(self, replacements, out_path, remove_prefixes=None):
        # replacements: dict path -> bytes (UTF-8). Keep all other files byte-identical.
        # We flatten all file nodes, then lay out data sequentially, updating offsets.
        files_nodes = []
        def collect(node, prefix):
            # node is a directory node: iterate its `files` mapping
            for name, child in (node.get('files') or {}).items():
                if 'files' in child:
                    collect(child, prefix + name + '/')
                elif 'offset' in child:
                    files_nodes.append((prefix + name, child))
        collect(self.header, '')

        # Read all original data once
        with open(self.path, 'rb') as f:
            f.seek(self.data_start)
            blob = f.read()

        out = io.BytesIO()
        new_header = json.loads(json.dumps(self.header))
        # Remove nodes whose path starts with any of remove_prefixes FIRST.
        if remove_prefixes:
            files_nodes = [(p,n) for p,n in files_nodes if not any(p.startswith(rp) for rp in remove_prefixes)]
            def prune(node, prefix):
                for name, child in list((node.get('files') or {}).items()):
                    p = prefix + name
                    if 'files' in child:
                        prune(child, p + '/')
                    elif 'offset' in child and any(p.startswith(rp) for rp in remove_prefixes):
                        del node['files'][name]
            prune(new_header, '')
        # Register any brand-new files into the header tree (after pruning).
        for newpath, data in replacements.items():
            if newpath in dict((p, n) for p, n in files_nodes):
                continue
            parts = [x for x in newpath.split('/') if x]
            node = new_header
            for part in parts[:-1]:
                if 'files' not in node:
                    node['files'] = {}
                if part not in node['files']:
                    node['files'][part] = {'files': {}}
                node = node['files'][part]
            if 'files' not in node:
                node['files'] = {}
            node['files'][parts[-1]] = {'offset': '0', 'size': len(data)}
            files_nodes.append((newpath, node['files'][parts[-1]]))
        # Rebuild header file tree offsets by writing each file in original order
        offset_map = {}
        for path, node in files_nodes:
            if path in replacements:
                data = replacements[path]
            else:
                off = int(node['offset']); size = int(node['size'])
                data = blob[off:off+size]
            offset_map[path] = (out.tell(), len(data))
            out.write(data)

        def update(node, prefix):
            for name, child in (node.get('files') or {}).items():
                p = prefix + name
                if 'files' in child:
                    update(child, p + '/')
                elif 'offset' in child:
                    off, size = offset_map[p]
                    child['offset'] = str(off); child['size'] = size
        update(new_header, '')

        header_bytes = json.dumps(new_header, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        jlen = len(header_bytes)
        # Match original 16-byte prefix layout exactly.
        prefix = struct.pack('<4sIII', b'\x04\x00\x00\x00', jlen + 8, jlen + 4, jlen)
        with open(out_path, 'wb') as f:
            f.write(prefix)
            f.write(header_bytes)
            f.write(out.getvalue())
        return len(header_bytes), out.tell()

if __name__ == '__main__':
    a = Asar(r'G:\anywhere\Agents Anywhere\resources\app.asar')
    print('data_start', a.data_start, 'string_len', a.string_len)
    print('top', a.list())
    # round-trip test: no replacements
    h, d = a.replace_and_write({}, r'C:\Users\sun67\AppData\Local\Temp\opencode\app_roundtrip.asar')
    print('roundtrip header', h, 'data', d)
    print('roundtrip size', os.path.getsize(r'C:\Users\sun67\AppData\Local\Temp\opencode\app_roundtrip.asar'))
    print('orig size', os.path.getsize(a.path))
