"""Consulta explícita e com cache: endereço -> ponto -> trajetos rodoviários dirigidos."""
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import json
import math
import re
import threading
import time
import unicodedata
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder

from .models import CacheConsultaMapas, MatrizDistancia, Unidade


_lock = threading.Lock()
_ultima_consulta = 0.0


def endereco_unidade(unidade):
    return ', '.join(str(v).strip() for v in (unidade.endereco, unidade.cidade, unidade.cep, 'Brasil') if v)


def assinatura_enderecos(origem, destino):
    texto = json.dumps([endereco_unidade(origem), endereco_unidade(destino)], ensure_ascii=False)
    return hashlib.sha256(texto.encode()).hexdigest()


def assinatura_matriz(origem, destino):
    from django.db.models import Q
    linhas = list(MatrizDistancia.objects.filter(Q(origem=origem, destino=destino) |
                 Q(origem=destino, destino=origem)).order_by('pk').values())
    return hashlib.sha256(json.dumps(linhas, cls=DjangoJSONEncoder, sort_keys=True).encode()).hexdigest()


def requisitar_json(url):
    """Um processo local, consultas serializadas <=1/s, sem retentativas em loop."""
    global _ultima_consulta
    if not settings.GRADE_MAPAS_HABILITADO:
        raise ValidationError('Consulta de mapas desabilitada neste ambiente.')
    with _lock:
        espera = 1.1 - (time.monotonic() - _ultima_consulta)
        if espera > 0:
            time.sleep(espera)
        _ultima_consulta = time.monotonic()
        try:
            req = Request(url, headers={'User-Agent': settings.GRADE_MAPAS_USER_AGENT,
                                       'Accept': 'application/json', 'Accept-Language': 'pt-BR'})
            with urlopen(req, timeout=8) as resposta:
                texto = resposta.read(1_000_001)
                if len(texto) > 1_000_000:
                    raise ValueError('Resposta grande demais')
                return json.loads(texto)
        except (URLError, TimeoutError, ValueError, OSError):
            raise ValidationError('O serviço de mapas não respondeu corretamente. Nenhum trajeto foi substituído; tente mais tarde.')


def consultar_cache(tipo, parametros, carregar):
    chave = hashlib.sha256(json.dumps([tipo, parametros], sort_keys=True).encode()).hexdigest()
    cache = CacheConsultaMapas.objects.filter(chave=chave, criado_em__gte=timezone.now()-timedelta(days=30)).first()
    if cache:
        return cache.dados
    dados = carregar()
    CacheConsultaMapas.objects.update_or_create(chave=chave, defaults={'dados': dados})
    return dados


def localizar(unidade):
    if not unidade.endereco or not unidade.cidade:
        raise ValidationError(f'{unidade.nome}: preencha e salve o endereço e a cidade antes de consultar.')
    consulta = endereco_unidade(unidade)
    url = settings.GRADE_GEOCODER_URL + '?' + urlencode({
        'q': consulta, 'format': 'jsonv2', 'limit': 2, 'countrycodes': 'br', 'addressdetails': 1})
    resultados = consultar_cache('geocode', url, lambda: requisitar_json(url))
    if not isinstance(resultados, list) or not resultados:
        raise ValidationError(f'{unidade.nome}: endereço não localizado. Confira número, cidade/UF e CEP.')
    if len(resultados) > 1:
        # Um mesmo prédio pode aparecer como edifício, equipamento e monumento.
        # Só agrupar quando município, rua, número e CEP são idênticos e os pontos
        # estão no mesmo quarteirão. Ruas/bairros diferentes continuam ambíguos.
        chaves = []
        for candidato in resultados:
            a = candidato.get('address', {})
            chaves.append(tuple(str(a.get(c, '')).casefold().strip()
                                for c in ('city', 'road', 'house_number', 'postcode')))
        try:
            proximos = (max(float(r['lat']) for r in resultados)-min(float(r['lat']) for r in resultados) <= .001
                        and max(float(r['lon']) for r in resultados)-min(float(r['lon']) for r in resultados) <= .001)
        except (KeyError, TypeError, ValueError):
            proximos = False
        cep = re.sub(r'\D', '', unidade.cep or '')
        numero = re.search(r',\s*(\d+)\b', unidade.endereco or '')
        exatos = (all(all(c) for c in chaves) and len(set(chaves)) == 1 and proximos
                  and (not cep or re.sub(r'\D', '', chaves[0][3]) == cep)
                  and (not numero or chaves[0][2] == numero.group(1)))
        if not exatos:
            raise ValidationError(f'{unidade.nome}: endereço ambíguo. Complete número, cidade/UF e CEP para identificar a escola.')
        resultados = [next((r for r in resultados if r.get('address', {}).get('amenity')), resultados[0])]
    try:
        item = resultados[0]
        endereco = item.get('address', {})
        municipio = next((endereco[c] for c in ('city', 'town', 'village', 'municipality') if endereco.get(c)), '')
        esperado = re.sub(r'\s*[,/-]\s*[A-Za-z]{2}\s*$', '', unidade.cidade).strip()
        def normalizar(texto):
            return ''.join(c for c in unicodedata.normalize('NFKD', texto.casefold()) if not unicodedata.combining(c)).strip()
        if not municipio or normalizar(municipio) != normalizar(esperado):
            raise ValidationError(f'{unidade.nome}: o serviço não confirmou o município cadastrado. '
                                  f'Resultado: {municipio or "município não informado"}. Confira cidade/UF, bairro e CEP.')
        lat, lon = float(item['lat']), float(item['lon'])
        if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise ValueError
        return {'lat': lat, 'lon': lon, 'rotulo': str(item['display_name'])[:600]}
    except (KeyError, ValueError, TypeError):
        raise ValidationError('O geocodificador retornou uma localização inválida. Nenhum trajeto foi aplicado.')


def trecho(a, b):
    coords = f"{a['lon']},{a['lat']};{b['lon']},{b['lat']}"
    url = settings.GRADE_ROTAS_URL.rstrip('/') + '/' + coords + '?overview=false&steps=false'
    resposta = consultar_cache('route', url, lambda: requisitar_json(url))
    try:
        if resposta['code'] != 'Ok':
            raise ValueError
        rota = resposta['routes'][0]
        metros, segundos = float(rota['distance']), float(rota['duration'])
        if not all(math.isfinite(v) and v >= 0 for v in (metros, segundos)):
            raise ValueError
        if metros > 999999990 or segundos > (2**31-1)*60:
            raise ValueError
        return {'km': str((Decimal(str(metros))/1000).quantize(Decimal('0.01'))),
                'minutos': math.ceil(segundos/60)}
    except (KeyError, ValueError, IndexError, TypeError):
        raise ValidationError('Não foi possível obter um trajeto rodoviário válido. O trajeto continua desconhecido.')


def consultar_trajeto(origem, destino):
    if origem.pk == destino.pk:
        raise ValidationError('Selecione outra unidade.')
    a, b = localizar(origem), localizar(destino)
    return {'origem_id': origem.pk, 'destino_id': destino.pk, 'hash': assinatura_enderecos(origem, destino),
            'matriz_hash': assinatura_matriz(origem, destino),
            'origem': a, 'destino': b, 'ida': trecho(a, b), 'volta': trecho(b, a),
            'consultado_em': timezone.now().isoformat()}


@transaction.atomic
def aplicar_trajeto(dados):
    origem = Unidade.objects.get(pk=dados['origem_id'])
    destino = Unidade.objects.get(pk=dados['destino_id'])
    if assinatura_enderecos(origem, destino) != dados['hash']:
        raise ValidationError('Os endereços mudaram desde a consulta. Consulte novamente.')
    if assinatura_matriz(origem, destino) != dados['matriz_hash']:
        raise ValidationError('Os trajetos foram editados após a consulta. Consulte novamente antes de substituir.')
    if timezone.now() - datetime.fromisoformat(dados['consultado_em']) > timedelta(minutes=30):
        raise ValidationError('A consulta expirou. Consulte novamente.')
    for a, b, trecho_dados in ((origem, destino, dados['ida']), (destino, origem, dados['volta'])):
        campos = {'tempo_minutos': trecho_dados['minutos'], 'distancia_km': Decimal(trecho_dados['km']),
                  'fonte': 'OSRM-carro', 'consultado_em': datetime.fromisoformat(dados['consultado_em']),
                  'enderecos_hash': assinatura_enderecos(a, b)}
        registros = MatrizDistancia.objects.filter(origem=a, destino=b)
        if not registros.update(**campos):
            MatrizDistancia.objects.create(origem=a, destino=b, **campos)
