import re
import random
import string
from api.eclass import EClass
from bs4 import BeautifulSoup as bs
from flask import Flask, request, session, jsonify

app = Flask(__name__)

def generate_random_hex(length):
    hex_characters = string.hexdigits[:-6]
    return ''.join(random.choice(hex_characters) for _ in range(length))

app.secret_key = generate_random_hex(16)

eclass_instance = None

@app.route('/')
def main():
    global eclass_instance
    if 'nim' in session and 'password' in session:
        nim = session['nim']
        password = session['password']
        if eclass_instance is None:
            eclass_instance = EClass(nim, password)
            if not eclass_instance.login():
                return jsonify({'message': 'Gagal masuk ke EClass'}), 401
        elif eclass_instance.session is None:
            if not eclass_instance.login():
                return jsonify({'message': 'Gagal masuk ke EClass'}), 401
    else:
        return jsonify({'message': 'Diperlukan login'}), 401

    return jsonify({'message': 'Selamat datang di API EClass UKDW (Unofficial)'}), 200

@app.route('/login', methods=['POST'])
def login():
    global eclass_instance
    data = request.json
    if 'nim' in data and 'password' in data:
        nim = data['nim']
        password = data['password']
        if eclass_instance is None or eclass_instance.session is None:
            eclass_instance = EClass(nim, password)
        else:
            eclass_instance = EClass(nim, password)

        if eclass_instance.login():
            session['nim'] = nim
            session['password'] = password
            return jsonify({'message': 'Berhasil login'}), 200
        else:
            return jsonify({'message': 'Gagal masuk ke EClass'}), 401
    else:
        return jsonify({'message': 'Anda belum memberikan nim atau password pada body request'}), 401

@app.route('/logout', methods=['GET'])
def logout():
    global eclass_instance
    session.pop('nim', None)
    session.pop('password', None)
    eclass_instance = None
    return jsonify({'message': 'Berhasil logout'}), 200

@app.route('/get_kelas', methods=['GET'])
def get_kelas():
    global eclass_instance
    if eclass_instance is None:
        return jsonify({'message': 'Instance EClass tidak tersedia. Silakan login terlebih dahulu'}), 401

    if not eclass_instance.session:
        return jsonify({'message': 'Sesi login tidak tersedia. Silakan login terlebih dahulu'}), 401

    eclass_session = eclass_instance.create_session()
    index_url = eclass_session.get('https://eclass.ukdw.ac.id/e-class/id/kelas/index')
    if index_url.status_code == 200:
        soup = bs(index_url.text, 'html.parser')
        # Kelas
        kelas_boxes = soup.find_all('div', class_='kelas_box')
        kelas_list = []
        for kelas_box in kelas_boxes:
            h2_elements = kelas_box.find_all('h2')
            for h2_element in h2_elements:
                text = h2_element.text.strip()
                text = re.sub(r'\s{2,}', ' ', text)
                match = re.match(r'\[(\w+)\]\s*(.*?)\s+([A-Z])\s*\((\d+)\s+SKS\)', text)
                if match:
                    kelas_dict = {
                        'id': match.group(1),
                        'matkul': match.group(2) + ' ' + match.group(3),
                        'sks': match.group(4) + ' SKS'
                    }
                    kelas_list.append(kelas_dict)

        return jsonify({'result': kelas_list}), 200
    else:
        return jsonify({'message': 'Gagal mendapatkan data kelas'}), index_url.status_code

@app.route('/get_materi/<id>', methods=['GET'])
def get_materi(id):
    global eclass_instance
    if eclass_instance is None:
        return jsonify({'message': 'Instance EClass tidak tersedia. Silakan login terlebih dahulu'}), 401

    if not eclass_instance.session:
        return jsonify({'message': 'Sesi login tidak tersedia. Silakan login terlebih dahulu'}), 401

    eclass_session = eclass_instance.create_session()
    materi_url = eclass_session.get(f'https://eclass.ukdw.ac.id/e-class/id/materi/index/{id}')
    
    if materi_url.status_code == 200:
        soup = bs(materi_url.text, 'html.parser')
        # Materi
        materi_list = []
        tables = soup.find_all('table', class_='data')
        if len(tables) >= 2:
            table = tables[1]
            rows = table.find_all('tr')
            for row in rows[1:]:
                cells = row.find_all('td')
                no = cells[0].text.strip()
                judul = cells[1].text.strip()
                jenis_file = cells[2].find('b').text.strip()
                ukuran_file = cells[2].find('span', class_='note').text.strip() if cells[2].find('span', class_='note') else 'O KB'
                url = cells[3].find('a')['href']
                
                materi_list.append({
                    'no': no,
                    'judul': judul,
                    'jenis_file': jenis_file,
                    'ukuran_file': ukuran_file,
                    'url': url
                })

        return jsonify({'result': materi_list}), 200
    else:
        return jsonify({'message': 'Gagal mendapatkan informasi materi'}), materi_url.status_code

@app.route('/get_tugas/<id>', methods=['GET'])
def get_tugas(id):
    global eclass_instance
    if eclass_instance is None:
        return jsonify({'message': 'Instance EClass tidak tersedia. Silakan login terlebih dahulu'}), 401

    if not eclass_instance.session:
        return jsonify({'message': 'Sesi login tidak tersedia. Silakan login terlebih dahulu'}), 401
    
    eclass_session = eclass_instance.create_session()
    tugas_url = eclass_session.get(f'https://eclass.ukdw.ac.id/e-class/id/kelas/tugas/{id}')

    if tugas_url.status_code == 200:
        # Tugas
        soup = bs(tugas_url.text, 'html.parser')
        tugas_list = []
        table = soup.find('table', class_='data')
        if table:
            rows = table.find_all('tr')
            for row in rows[1:]:
                cells = row.find_all('td')
                no = cells[0].text.strip()
                judul = cells[1].text.strip()
                started_at = cells[2].text.strip()
                closed_at = cells[3].text.strip()
                details = cells[4].find('a')['href']

                tugas_list.append({
                    'no': no,
                    'id': re.search(r"\d+", details).group(),
                    'judul': judul,
                    'started_at': started_at,
                    'closed_at': closed_at,
                    'detail': details
                })
        return jsonify({'result': tugas_list}), 200
    else:
        return jsonify({'message': 'Gagal mendapatkan informasi tugas'}), tugas_url.status_code
    
@app.route('/get_daftar_pengumuman', methods=['GET'])
def get_daftar_pengumuman():
    global eclass_instance
    if eclass_instance is None:
        return jsonify({'message': 'Instance EClass tidak tersedia. Silakan login terlebih dahulu'}), 401

    if not eclass_instance.session:
        return jsonify({'message': 'Sesi login tidak tersedia. Silakan login terlebih dahulu'}), 401

    eclass_session = eclass_instance.create_session()
    index_url = eclass_session.get('https://eclass.ukdw.ac.id/e-class/id/kelas/index')

    if index_url.status_code == 200:
        # Pengumuman
        soup = bs(index_url.text, 'html.parser')
        list_pengumuman = soup.find_all('a', {'class': 'menu mc'})
        pengumuman_terbaru = []
        pengumuman_tugas = []

        for pengumuman in list_pengumuman:
            url = pengumuman["href"]
            content = pengumuman.stripped_strings
            tanggal = next(content)
            next(content)
            judul = next(content)

            if re.search(r"\d+", url).group().startswith('6'):
                pengumuman_tugas.append({
                    'id': re.search(r"\d+", url).group(),
                    'judul': judul[1:],
                    'mata_kuliah': pengumuman['title'],
                    'date': tanggal,
                })
            else:
                pengumuman_terbaru.append({
                    'id': re.search(r"\d+", url).group(),
                    'judul': judul[1:],
                    'mata_kuliah': pengumuman['title'],
                    'date': tanggal,
                })

        pengumuman_list = { "pengumuman": pengumuman_terbaru, "tugas": pengumuman_tugas }
        return jsonify({'result': pengumuman_list}), 200
    else:
        return jsonify({'message': 'Gagal mendapatkan informasi tugas'}), index_url.status_code

@app.route('/get_detail_pengumuman/<id>', methods=['GET'])
def get_detail_pengumuman(id):
    global eclass_instance
    if eclass_instance is None:
        return jsonify({'message': 'Instance EClass tidak tersedia. Silakan login terlebih dahulu'}), 401

    if not eclass_instance.session:
        return jsonify({'message': 'Sesi login tidak tersedia. Silakan login terlebih dahulu'}), 401

    eclass_session = eclass_instance.create_session()
    pengumuman_url = eclass_session.get(f'https://eclass.ukdw.ac.id/e-class/id/pengumuman/baca/{id}')

    if pengumuman_url.status_code == 200:
        # Detail Pengumuman
        soup = bs(pengumuman_url.text, 'html.parser')
        pengumuman = soup.find('div', {'id': 'content-right'})
        header = pengumuman.find('tr', {'class': 'thread'}).td
        header = header.stripped_strings
        judul = next(header)
        tanggal = next(header)

        # Isi Pengumuman
        isi = pengumuman.find('tr', {'class': 'isithread'}).td
        isi = isi.stripped_strings
        result_isi = [re.sub(r'\s+', ' ', content) for content in isi]
        matkul = result_isi[1]
        dosen = result_isi[-1]
        isi_pengumuman = ' '.join(result_isi[2:-1])

        result = {
            'id': id,
            'matkul': matkul,
            'dosen': dosen,
            'judul': judul,
            'tanggal': tanggal,
            'isi_pengumuman': isi_pengumuman
        }

        return jsonify({'result': result}), 200
    else:
        return jsonify({'message': 'Gagal mendapatkan informasi detail pengumuman'}), pengumuman_url.status_code

@app.route('/get_detail_tugas/<id>', methods=['GET'])
def get_detail_tugas(id):
    global eclass_instance
    if eclass_instance is None:
        return jsonify({'message': 'Instance EClass tidak tersedia. Silakan login terlebih dahulu'}), 401

    if not eclass_instance.session:
        return jsonify({'message': 'Sesi login tidak tersedia. Silakan login terlebih dahulu'}), 401

    eclass_session = eclass_instance.create_session()
    tugas_url = eclass_session.get(f'https://eclass.ukdw.ac.id/e-class/id/kelas/detail_tugas/{id}')

    if tugas_url.status_code == 200:
        soup = bs(tugas_url.text, 'html.parser')
        tables = soup.find_all('table', class_='diskusi')

        if len(tables) >= 2:
            table = tables[1]
            background_color = table.find('div')['style']
            is_closed = 'red' in background_color

            judul = table.find('td').text.strip()
            started_at = table.find('span', class_='tgl').text.strip()
            judul = judul.replace(started_at, '')

            result = {
                'is_closed': is_closed,
                'judul': judul,
                'started_at': started_at,
                'url': f'https://eclass.ukdw.ac.id/e-class/id/kelas/detail_tugas/{id}'
            }
        return jsonify({'result': result}), 200
    else:
        return jsonify({'message': 'Gagal mendapatkan informasi detail tugas'}), tugas_url.status_code

@app.route('/get_presensi/<id>', methods=['GET'])
def get_presensi(id):
    global eclass_instance
    if eclass_instance is None:
        return jsonify({'message': 'Instance EClass tidak tersedia. Silakan login terlebih dahulu'}), 401

    if not eclass_instance.session:
        return jsonify({'message': 'Sesi login tidak tersedia. Silakan login terlebih dahulu'}), 401

    eclass_session = eclass_instance.create_session()
    presensi_url = eclass_session.get(f'https://eclass.ukdw.ac.id/e-class/id/kelas/presensi/{id}')

    if presensi_url.status_code == 200:
        soup = bs(presensi_url.text, 'html.parser')
        form = soup.find('form')

        if form is None:
            return jsonify({'error': 'Presensi belum tersedia'})

        p_pertemuanke_input = form.find('input', {'name': 'p_pertemuanke'})
        p_idpresensi_input = form.find('input', {'name': 'p_idpresensi'})

        if p_pertemuanke_input is None or p_idpresensi_input is None:
            return jsonify({'error': 'Presensi belum terbuka!'})

        p_pertemuanke = p_pertemuanke_input.get('value')
        p_idpresensi = p_idpresensi_input.get('value')

        post_data = {
            'presensi_hadir': 'HADIR',
            'p_pertemuanke': p_pertemuanke,
            'p_idpresensi': p_idpresensi
        }

        response = eclass_session.post(presensi_url.url, data=post_data)

        if response.status_code == 200:
            return jsonify({'message': 'Presensi berhasil'})
        else:
            return jsonify({'error': 'Presensi gagal'})

@app.errorhandler(404)
def page_not_found(e):
    return jsonify({"status": 404, "message": "Not Found"}), 404

if __name__ == '__main__':
    app.run(debug=True)