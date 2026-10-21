# Imagens de teste

Esta pasta guarda fotos locais para validar o cadastro facial do Marco 3 e a chamada por reconhecimento do Marco 4. Ela **não faz parte do fluxo de login**.

## Estrutura

```text
imagens_teste/
  pessoa1/
  pessoa2/
  pessoa3/
```

- `pessoa1`: primeira pessoa de teste.
- `pessoa2`: segunda pessoa de teste.
- `pessoa3`: terceira pessoa de teste.

As pastas são criadas pelo `setup.bat`. Algumas imagens locais podem já existir; elas são ignoradas pelo Git e não devem ser enviadas ao repositório.

## Formato recomendado

- 3 a 5 fotos por pessoa.
- Arquivos `.jpg`, `.jpeg`, `.png` ou `.webp`.
- Rosto frontal, bem iluminado e sem acessórios que escondam os olhos.
- Variar levemente expressão, ângulo e iluminação entre as fotos.
- Uma pessoa por foto, com o rosto ocupando a maior parte do enquadramento.
- Evitar fotos borradas, muito escuras, com filtros fortes ou com outras pessoas ao fundo.

## Privacidade

Fotos de rosto são dados pessoais sensíveis. Use apenas imagens de pessoas que autorizaram o teste, mantenha os arquivos somente na máquina local e não faça commit dessa pasta.

## Como validar o modelo

Com o projeto instalado e o modelo em `data/insightface/models/buffalo_l`, execute a partir da raiz:

```bat
venv\Scripts\python.exe scripts\check_face_model.py imagens_teste\pessoa2
```

O script:

- lê todas as imagens suportadas da pasta;
- confirma que há exatamente um rosto detectado em cada foto;
- calcula a similaridade entre todos os pares;
- falha se a menor similaridade ficar abaixo de `0.30`.

Para usar outro limite:

```bat
venv\Scripts\python.exe scripts\check_face_model.py imagens_teste\pessoa2 --min-similarity 0.35
```

Use uma pasta por pessoa. Não misture fotos de pessoas diferentes na mesma pasta: o script interpreta todas como capturas da mesma pessoa. A rejeição de outra pessoa no cadastro é validada separadamente pela interface e pelos testes.

## Chamada do Marco 4

Para validar a chamada no banco isolado do E2E:

1. cadastre `rafael@lins.com.br` com as três fotos de `pessoa2`;
2. mantenha `beatriz@lins.com.br` sem cadastro facial;
3. abra a chamada da turma como instrutor e envie uma foto de `pessoa2`, que deve ser reconhecida;
4. envie uma foto de `pessoa3`, que deve ser recusada como pessoa fora da turma;
5. registre Beatriz manualmente para validar o fallback.

A câmera simulada do Chromium serve para validar o preview, mas o upload de arquivo é o caminho recomendado para testar o reconhecimento real em E2E.

O modelo `buffalo_l` está licenciado para uso não comercial; consulte a observação no README principal.
