# Trilha de Talentos

Plataforma de capacitação da Lins Agroindustrial: o RH cadastra treinamentos, líderes reservam vagas para o time, instrutores registram presença com reconhecimento facial e o sistema emite certificados verificáveis.

Este repositório contém a versão local do projeto, desenvolvida em marcos. **Os Marcos 1, 2, 3, 4, 5 e 6 estão implementados**: instalação, banco local, autenticação, troca de senha obrigatória, painéis por perfil, CRUD de pessoas e treinamentos pelo RH, reservas de vagas pelo líder, caixa de saída de e-mails, cadastro facial com consentimento LGPD, chamada de presença com reconhecimento facial e fallback manual, encerramento de turmas, certificados verificáveis em PDF com QR Code e teste de carga local.

## Situação atual

### Funciona nesta entrega

- Instalação automatizada no Windows com criação de `venv`, banco SQLite, seed e build do frontend.
- Login por e-mail e senha, sem seletor manual de perfil e sem menu lateral.
- Sessão assinada em cookie, CSRF, hash Argon2, bloqueio temporário após tentativas de login e auditoria básica.
- Redirecionamento automático por perfil: RH, líder, instrutor e funcionário.
- Troca obrigatória de senha no primeiro acesso.
- Painéis iniciais mobile-first para os quatro perfis.
- Página pública `/verificar` e rota `/verificar/:codigo` para consulta de certificados.
- Acesso pelo computador e por celular na mesma rede Wi-Fi.
- CRUD de pessoas pelo RH em `/rh/pessoas`, com perfis, vínculo de líder, ativação/desativação, senha temporária e reset de senha.
- CRUD de treinamentos em `/rh/trainings`, com instrutor, data, horário, local, vagas, carga horária, cancelamento e exclusão protegida.
- Reservas de vagas em lote pelo líder em `/lider/reservas`, com validação de capacidade, duplicidade e cancelamento.
- Caixa de saída em `/rh/outbox`, com busca, status de envio e cópia das credenciais/notificações.
- Notificações por e-mail persistidas no outbox; envio SMTP opcional por configuração.
- Termo de consentimento LGPD versionado em `/cadastro-facial`, com aceite registrado e possibilidade de revogação.
- Cadastro facial guiado com câmera ou upload de foto, três capturas, verificação de qualidade e consistência biométrica.
- Modelo `buffalo_l` carregado localmente em CPU na inicialização do servidor.
- Revogação do consentimento que exclui consentimento e vetores faciais do usuário, com registro da ação na auditoria.
- Chamada de presença do instrutor em `/instrutor/chamadas/:id`, com progresso, busca de participantes, câmera ou upload, reconhecimento facial e fallback manual justificado.
- Bloqueio de chamadas canceladas, concluídas ou sem reservas ativas; aviso, sem bloqueio, quando a turma não é do dia.
- Remoção de presença pelo instrutor enquanto a turma não estiver concluída, com atualização do resumo e auditoria.
- Encerramento de turma pelo instrutor, com emissão automática de certificados para os participantes presentes e código único de verificação.
- Certificados visíveis no painel do funcionário e verificáveis publicamente por código.
- Bloqueio de novas presenças, remoção de presença e cancelamento de reservas após a conclusão da turma.
- Certificado em PDF A4 com identidade visual, código, QR Code e link de verificação; download público e pelo painel do funcionário.
- Teste de carga local configurável para health, verificação, QR Code e PDF.
- Testes automatizados da API e das regras de segurança dos Marcos 1, 2, 3, 4, 5 e 6.

### Não incluído nesta versão

- Envio real de e-mail no ambiente de demonstração: sem SMTP configurado, as mensagens ficam no outbox. O envio é opcional via `.env`.
- Assinatura digital certificada ICP-Brasil ou carimbo de tempo: o PDF é autenticável pelo código e pelo QR Code, mas não possui assinatura criptográfica de autoridade certificadora.
- Integrações com sistemas externos de RH ou emissão em lote fora do fluxo de encerramento de turma.

O modelo facial é carregado na inicialização e pode acrescentar alguns segundos ao primeiro start. O cadastro do rosto e a chamada com reconhecimento estão ativos. Todos os marcos planejados estão disponíveis nesta versão.

## Stack

| Camada                | Tecnologia                                                             |
| --------------------- | ---------------------------------------------------------------------- |
| Frontend              | React 19, Vite 7, TypeScript, Tailwind CSS 4, componentes Radix/shadcn |
| Backend               | FastAPI, SQLAlchemy, Pydantic                                          |
| Banco                 | SQLite local em `data/app.db`                                          |
| Autenticação          | Argon2, cookie assinado com `itsdangerous`, CSRF double-submit         |
| Reconhecimento facial | InsightFace `buffalo_l` + ONNX Runtime, CPU; cadastro e chamada        |
| Testes                | Pytest + FastAPI TestClient                                            |

Não há Docker, banco externo, armazenamento em nuvem ou serviço pago obrigatório.

## Requisitos

- Windows 10 ou 11.
- Python 3.10 a 3.12. Recomendado: **Python 3.12**.
- Node.js 20 ou superior, com npm.
- Cerca de 1 GB livre para a `venv`, dependências e modelo facial.
- Internet na primeira instalação para baixar as dependências e o modelo `buffalo_l` (~325 MB).
- Celular e computador na mesma rede Wi-Fi para o teste mobile.

## Instalação

Na raiz do projeto, execute:

```bat
setup.bat
```

Também é possível executar sem perguntas:

```bat
setup.bat -Seed -NoHttps
```

O script:

1. localiza Python 3.10–3.12 e cria/valida a `venv`;
2. instala as dependências Python;
3. valida InsightFace, ONNX Runtime e OpenCV;
4. cria o `.env` com uma `SECRET_KEY` aleatória;
5. baixa o modelo facial `buffalo_l` para `data/insightface/models/buffalo_l`;
6. inicializa o SQLite em `data/app.db`;
7. instala as dependências Node, se necessário, e compila o frontend em `dist/`;
8. executa o seed idempotente.

Opções úteis do setup:

```bat
setup.bat -NoModel
setup.bat -NoFrontend
setup.bat -NoSeed
setup.bat -Https
```

Para instalar sem baixar o modelo, use `-NoModel`. O cadastro facial depende do modelo; sem ele, a API responde `503` com uma mensagem de configuração.

## Como iniciar

```bat
start.bat
```

O terminal exibirá dois endereços:

- computador: `http://127.0.0.1:8000`;
- celular: `http://IP-DA-MAQUINA:8000` (mesma rede Wi-Fi).

Mantenha o terminal aberto e use `Ctrl+C` para encerrar. Se a porta 8000 estiver ocupada:

```bat
start.bat --port 8001
```

### Liberar o acesso pelo celular

Na primeira execução, o Windows pode pedir permissão de firewall. Permita o acesso em redes privadas. Se necessário, execute em um terminal **como Administrador**:

```bat
netsh advfirewall firewall add rule name="Trilha de Talentos 8000" dir=in action=allow protocol=TCP localport=8000
```

Se o celular não abrir o endereço:

- confirme que os dois aparelhos estão na mesma rede;
- não use `localhost` no celular;
- confirme o IP mostrado pelo `start.bat`;
- verifique se a rede Wi-Fi está marcada como privada no Windows;
- libere a porta no firewall.

## Credenciais de teste

| Perfil      | E-mail                  | Senha                | Observação                   |
| ----------- | ----------------------- | -------------------- | ---------------------------- |
| RH          | `rh@lins.com.br`        | `LinsRh@2026`        | Acesso ao painel do RH       |
| Líder       | `lider@lins.com.br`     | `LinsLider@2026`     | Equipe com três funcionários |
| Instrutor   | `instrutor@lins.com.br` | `LinsInstrutor@2026` | Três turmas de exemplo       |
| Funcionário | `rafael@lins.com.br`    | `Rafael@2026`        | Troca de senha obrigatória   |
| Funcionário | `beatriz@lins.com.br`   | `Beatriz@2026`       | Troca de senha obrigatória   |
| Funcionário | `joao@lins.com.br`      | `Joao@2026`          | Troca de senha obrigatória   |

Essas contas são apenas para desenvolvimento local. As senhas dos funcionários são temporárias e precisam ser alteradas no primeiro acesso. O seed preserva senhas já alteradas quando executado novamente. Para repetir o teste de primeiro acesso, veja [Resetar os dados de teste](#resetar-os-dados-de-teste).

## Marco 2: operação do RH e líder

| Rota              | Perfil | Função                                                         |
| ----------------- | ------ | -------------------------------------------------------------- |
| `/rh/pessoas`     | RH     | Cadastro, edição, ativação, reset de senha e vínculo de líder. |
| `/rh/trainings`   | RH     | Cadastro, edição, cancelamento e exclusão de turmas.           |
| `/rh/outbox`      | RH     | Consulta das notificações e credenciais geradas pelo sistema.  |
| `/lider/reservas` | Líder  | Reserva em lote para o time e cancelamento de reservas.        |

Regras principais:

- funcionário precisa estar vinculado a um líder ativo;
- e-mails são normalizados e não podem duplicar;
- o RH não pode desativar a própria conta nem o último RH ativo;
- líder com equipe, instrutor com turmas ativas e pessoa com reservas ativas não podem ser desativados;
- `Novo treinamento` exige data futura, horário válido e instrutor ativo;
- as vagas não podem ficar abaixo do número de reservas ativas;
- o líder só enxerga e reserva para as pessoas da própria equipe;
- reservas em lote são all-or-nothing e evitam duplicidade;
- cancelar uma turma cancela as reservas ativas e gera notificações;
- exclusão de turma só é permitida quando não há reservas, presenças ou certificados.

A senha temporária de um novo cadastro (ou de um reset) aparece no modal de credenciais e também no outbox. O outbox é restrito ao RH porque contém dados sensíveis. Com `SMTP_HOST` vazio, nenhuma mensagem sai do computador; para envio real, configure no `.env`:

```dotenv
SMTP_HOST=smtp.seudominio.com
SMTP_PORT=587
SMTP_USER=usuario
SMTP_PASSWORD=senha
SMTP_FROM=nao-responda@seudominio.com
SMTP_USE_TLS=true
```

Mesmo com SMTP configurado, a mensagem é registrada no outbox antes da tentativa de envio. Para testar o fluxo de e-mails sem servidor externo, mantenha o SMTP vazio e use `/rh/outbox`.

## Marco 3: cadastro facial

Qualquer pessoa autenticada com a senha já trocada pode abrir `/cadastro-facial`. Funcionários também encontram o convite no painel inicial. A tela não faz identificação automática: ela cria a biometria local que é usada pelo instrutor na chamada do Marco 4.

Fluxo:

1. ler o termo de consentimento LGPD, versão 1.0, e marcar o aceite;
2. liberar a câmera ou escolher uma foto como alternativa;
3. enquadrar um único rosto e tirar três capturas;
4. conferir o progresso e concluir o cadastro.

O servidor valida formato e tamanho do arquivo, resolução mínima, presença de exatamente um rosto, qualidade da detecção e consistência entre as capturas. Se as fotos parecerem de pessoas diferentes, a amostra é recusada e o progresso não avança.

Privacidade e armazenamento:

- nenhuma foto original é gravada; o banco guarda somente o vetor facial de 512 dimensões e metadados de qualidade;
- o cadastro só começa após consentimento explícito da versão atual do termo;
- `Refazer cadastro` apaga os vetores e mantém o consentimento;
- `Revogar consentimento` apaga consentimento e vetores, desativa `face_enrolled` e mantém a evidência da revogação na auditoria;
- o reconhecimento facial continua sendo processado localmente, em CPU, sem enviar imagens a serviços externos.

Em celular, a câmera ao vivo exige HTTPS; use `start.bat --https` e aceite o certificado de desenvolvimento. Em computador sem câmera, ou quando a permissão não estiver disponível, o upload de uma foto permite concluir o mesmo fluxo.

| Rota                           | Método | Função                                                   |
| ------------------------------ | ------ | -------------------------------------------------------- |
| `/api/face/term`               | GET    | Termo LGPD vigente.                                      |
| `/api/face/status`             | GET    | Consentimento, amostras e situação do cadastro.          |
| `/api/face/consent`            | POST   | Registrar o aceite da versão atual.                      |
| `/api/face/consent`            | DELETE | Revogar consentimento e excluir os dados faciais.        |
| `/api/face/enrollment`         | DELETE | Apagar apenas as capturas e permitir refazer o cadastro. |
| `/api/face/enrollment/samples` | POST   | Validar e gravar uma captura (máximo de três).           |

Para validar o modelo com fotos locais antes de testar a interface:

```bat
venv\Scripts\python.exe scripts\check_face_model.py imagens_teste\pessoa2
```

O script compara todas as fotos da pasta e falha se a similaridade mínima configurada (`0.30`) não for atingida. Veja também [imagens_teste/README.md](imagens_teste/README.md).

Se o `.env` de uma instalação antiga ainda estiver com `FACE_MODEL_PRELOAD=false`, altere para `true` e reinicie o servidor. O modelo é carregado uma única vez por processo.

## Marco 4: chamada e presença

O instrutor abre a chamada pelo painel `/instrutor` no botão **Abrir chamada** ou diretamente em `/instrutor/chamadas/:id`. A página mostra a turma, o progresso, os participantes pendentes e as presenças já registradas.

Fluxo:

1. o instrutor confere a turma e os participantes com reserva ativa;
2. usa a câmera ou envia uma foto para reconhecer uma pessoa por vez;
3. se o rosto não for reconhecido, houver ambiguidade ou a pessoa não tiver cadastro facial, confirma a presença manualmente com um motivo;
4. acompanha o resumo facial/manual e pode remover uma presença enquanto a turma não estiver concluída.

Regras principais:

- o instrutor só acessa turmas atribuídas a ele;
- a chamada é permitida em turmas `agendado` ou `em_andamento` e exige ao menos uma reserva ativa;
- turmas `cancelado`, `concluido` ou sem participantes ficam bloqueadas;
- a comparação facial considera somente participantes com reserva ativa e `face_enrolled=true`;
- o melhor candidato precisa superar o limiar facial (`FACE_THRESHOLD`, padrão `0.45`) e ter margem sobre o segundo colocado (`FACE_MARGIN`, padrão `0.05`);
- o registro manual exige justificativa de 5 a 300 caracteres e é permitido mesmo sem cadastro facial;
- registrar novamente a mesma presença facial é idempotente; o registro manual duplicado retorna conflito;
- fora da data da turma, a tela mostra um aviso, mas não bloqueia a chamada;
- a remoção é bloqueada quando a turma está concluída;
- nenhuma imagem original é armazenada; o reconhecimento acontece localmente em CPU.

| Rota                                                        | Método | Função                                        |
| ----------------------------------------------------------- | ------ | --------------------------------------------- |
| `/api/instructor/trainings/{training_id}/attendance`        | GET    | Participantes, presenças, resumo e bloqueios. |
| `/api/instructor/trainings/{training_id}/attendance/face`   | POST   | Reconhecer rosto e registrar presença facial. |
| `/api/instructor/trainings/{training_id}/attendance/manual` | POST   | Registrar presença manual com justificativa.  |
| `/api/instructor/trainings/{training_id}/attendance/{id}`   | DELETE | Remover uma presença da turma.                |

Para testar com reconhecimento facial no banco de demonstração, entre primeiro como funcionário `rafael@lins.com.br`, conclua o cadastro facial usando as fotos de `imagens_teste/pessoa2` e depois abra a turma NR-12 como instrutor. A foto de `imagens_teste/pessoa3` serve para validar a recusa de uma pessoa fora da turma. O registro manual continua disponível para `beatriz@lins.com.br`, que começa sem cadastro facial.

## Marco 5: encerramento e certificação

O instrutor encerra a turma pela própria tela de chamada, no botão **Encerrar turma**. Ao confirmar, a turma passa para `concluido`, recebe `completed_at` e o sistema emite um certificado para cada participante com presença registrada. Participantes que continuarem pendentes não recebem certificado.

Regras principais:

- somente o instrutor responsável pela turma pode encerrá-la;
- o encerramento é permitido em turmas `agendado` ou `em_andamento` com ao menos uma reserva ativa;
- turmas `cancelado`, `concluido` ou sem participantes são bloqueadas;
- presenças pendentes não impedem o encerramento: elas ficam inelegíveis e a interface mostra o aviso antes da confirmação;
- presença facial e presença manual têm o mesmo direito ao certificado;
- uma turma sem nenhuma presença pode ser encerrada, mas não gera certificados;
- o código de verificação segue o formato `LINS-XXXXX-XXXXX-XXXXX` e é único;
- existe no máximo um certificado por treinamento/funcionário;
- depois da conclusão, não é possível registrar ou remover presenças nem cancelar reservas da turma;
- cada certificado gera uma notificação no outbox e um evento de auditoria;
- o certificado pode ser consultado em `/verificar/:codigo`, sem login.

| Rota                                                       | Método | Função                                                |
| ---------------------------------------------------------- | ------ | ----------------------------------------------------- |
| `/api/instructor/trainings/{training_id}/complete`         | POST   | Encerrar a turma e emitir os certificados elegíveis.  |
| `/api/certificates/verify/{code}`                          | GET    | Consulta pública de autenticidade do certificado.     |

Para testar, abra como instrutor uma turma ativa com reservas (por exemplo, Boas Práticas de Fabricação no banco principal ou NR-12 em um banco isolado), registre a presença de um participante e deixe outro pendente. Confirme **Encerrar turma**: será emitido somente o certificado de quem tem presença. O código aparece na lista de presenças, no painel do funcionário e na página pública de verificação. A turma fica imutável para novas presenças e cancelamentos. O PDF e o QR Code fazem parte do Marco 6.

## Marco 6: PDF, QR Code e carga

Cada certificado emitido pode ser baixado em PDF A4, com a identidade visual da Lins, dados do participante e do treinamento, código de verificação, URL pública e QR Code. A geração acontece localmente, sem serviço externo.

- o PDF é montado em memória com `reportlab` e não é persistido no banco;
- o QR Code é gerado com `qrcode` e aponta para `/verificar/:codigo`;
- o mesmo PDF pode ser baixado pela página pública ou pelo painel do funcionário;
- o e-mail de emissão agora inclui o link direto para o PDF;
- o QR usa `PUBLIC_BASE_URL` quando configurado e, caso contrário, o endereço pelo qual a requisição chegou;
- para o celular conseguir abrir o QR, prefira configurar `PUBLIC_BASE_URL` com o IP da LAN, por exemplo `http://192.168.68.150:8000`.

| Rota                                            | Método | Função                                               |
| ----------------------------------------------- | ------ | ---------------------------------------------------- |
| `/api/certificates/verify/{code}/pdf`           | GET    | Baixar o certificado em PDF, sem exigir login.        |
| `/api/certificates/verify/{code}/qr.png`        | GET    | Gerar a imagem PNG do QR Code de verificação.         |
| `/api/certificates/verify/{code}`               | GET    | Consultar os dados públicos do certificado.           |

Para testar, abra um certificado em `/verificar/:codigo`, confira o QR Code, clique em **Baixar PDF** e abra o arquivo. O painel do funcionário também oferece o atalho **PDF**. O PDF é autenticável pelo código/QR, mas ainda não possui assinatura digital ICP-Brasil.

O teste de carga usa apenas endpoints públicos e pode ser executado com:

```bat
venv\Scripts\python.exe scripts\load_test.py --base-url http://127.0.0.1:8000 --code LINS-XXXXX-XXXXX-XXXXX --endpoint mixed --requests 120 --concurrency 12
```

## Desenvolvimento

Backend com recarga automática:

```bat
venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Frontend com recarga automática, em outro terminal:

```bat
npm run dev
```

O Vite abre em `http://localhost:5173` e encaminha `/api` para `http://127.0.0.1:8000`.

Comandos úteis:

```bat
npm run typecheck
npm run lint
npm run build
venv\Scripts\python.exe -m pytest
```

Com `DEV_MODE=true`, a documentação da API fica em `http://127.0.0.1:8000/api/docs` e `http://127.0.0.1:8000/api/openapi.json`.

## Testes automatizados

A suíte atual cobre:

- login dos quatro perfis;
- redirecionamento por perfil;
- bloqueio de acesso sem sessão;
- exigência de CSRF;
- troca de senha obrigatória e liberação do painel;
- certificado inexistente;
- resposta 404 JSON para rotas de API desconhecidas;
- documentação interativa e CSP do Swagger UI;
- hash e força de senha;
- formato e unicidade dos códigos de certificado;
- cadastro de pessoas, e-mail duplicado, vínculo de líder, reset de senha e guardas de desativação;
- criação, edição, cancelamento e exclusão protegida de treinamentos;
- reservas em lote do líder, limite de vagas, duplicidade e cancelamento;
- outbox e notificações geradas pelas movimentações;
- termo e aceite de consentimento facial, incluindo versão e CSRF;
- cadastro facial com três amostras, limite, consistência, reset e revogação;
- exclusão dos vetores e do consentimento na revogação;
- mapeamento de falhas de qualidade e indisponibilidade do modelo;
- acesso do instrutor somente às próprias turmas e bloqueio de chamadas canceladas ou vazias;
- chamada facial com candidatos da reserva, limiar, margem, duplicidade idempotente e modelo indisponível;
- fallback manual com justificativa, validação de reserva ativa, CSRF e remoção de presença;
- encerramento de turma com certificado apenas para presentes, código único, verificação pública, outbox e auditoria;
- bloqueio de encerramento para turma cancelada, vazia ou já concluída, e imutabilidade após a conclusão;
- download público do certificado em PDF, QR Code em PNG, cabeçalho e filename do PDF;
- link do PDF no e-mail de emissão e pluralização dos avisos de pendentes.

Execute:

```bat
venv\Scripts\python.exe -m pytest
```

Resultado esperado: `35 passed`. Os testes de API usam um serviço facial simulado para não carregar o modelo em toda execução. Pode aparecer um aviso de depreciação do `TestClient` do Starlette relacionado à versão do `httpx`; ele não afeta a aplicação.

O roteiro de validação manual está em [TESTES_MANUAIS.md](TESTES_MANUAIS.md).

## Estrutura do projeto

```text
app/
  main.py          FastAPI, segurança HTTP e fallback da SPA
  config.py        Configurações do .env
  database.py      Conexão SQLite e sessões
  models.py        Modelos de domínio
  deps.py          Guards de autenticação e papéis
  security.py      Argon2, sessão, CSRF e rate limit
  routers/         Auth, home, verificação, RH, líder, rosto, chamada, conclusão e PDF
  services/        Auditoria, e-mail/outbox, treinamentos, consentimento, rosto, certificação e PDF

src/
  App.tsx          Rotas e guards da SPA
  pages/           Login, painéis, RH, liderança, troca de senha, verificação, rosto e chamada
  components/      Shell mobile, marca, status e componentes de UI
  lib/             Cliente HTTP, autenticação, roteador e formatação

scripts/
  setup.ps1        Instalação completa no Windows
  run_server.py    Inicialização local e endereço de rede
  seed.py          Dados de demonstração idempotentes
  download_model.py
  check_face_model.py  Validação local de fotos com o modelo real
  bootstrap_env.py
  init_db.py
  make_cert.py
  load_test.py     Teste de carga dos endpoints públicos

tests/             Testes Pytest
imagens_teste/     Fotos locais para os testes faciais (ver README da pasta)
data/              Banco, logs, certificados e modelo (ignorados pelo Git)
dist/              Frontend compilado (gerado)
```

## Banco e dados locais

- Banco: `data/app.db`.
- Modelo facial: `data/insightface/models/buffalo_l`.
- Certificados e materiais gerados: `data/certificates`.
- Fotos de teste: `imagens_teste/pessoa1`, `pessoa2` e `pessoa3`.
- `.env` e `data/` são ignorados pelo Git.
- O SQLite usa WAL; pare o servidor antes de copiar ou apagar o banco.

### Resetar os dados de teste

Isso apaga usuários, reservas e demais dados locais. Use somente no ambiente de desenvolvimento.

```powershell
# pare o servidor com Ctrl+C
Remove-Item data\app.db, data\app.db-wal, data\app.db-shm -ErrorAction SilentlyContinue
venv\Scripts\python.exe scripts\init_db.py
venv\Scripts\python.exe scripts\seed.py
```

Depois, inicie novamente com `start.bat`.

## HTTPS local

O uso de câmera ao vivo em celular exige um contexto seguro. O servidor já aceita HTTPS:

```bat
start.bat --https
```

O certificado autoassinado é gerado em `data/certs/`. O celular exibirá um aviso de segurança; aceite o certificado no teste local. Como é um certificado autoassinado, não use essa configuração em produção.

## Segurança, privacidade e LGPD

- Senhas são armazenadas com Argon2.
- A sessão usa cookie `HttpOnly`, `SameSite=Lax` e assinatura criptográfica.
- Rotas mutáveis exigem CSRF.
- Logins com falha são limitados por IP/e-mail.
- A aplicação registra auditoria de login, falha de login, logout, troca/reset de senha, movimentações de pessoas, treinamentos, reservas, presenças e certificados, além de aceite, captura, conclusão, reset e revogação facial.
- O projeto foi projetado para uso em rede local. Não exponha a porta 8000 diretamente à internet.
- Em produção, use HTTPS real, `DEV_MODE=false`, `SESSION_COOKIE_SECURE=true`, uma `SECRET_KEY` exclusiva e backup do banco.
- Fotos e dados biométricos são dados pessoais sensíveis. O cadastro facial exige consentimento explícito, armazena somente vetores e permite revogação com exclusão dos dados; revise o termo com o jurídico antes de uso real.
- As imagens em `imagens_teste/` não devem ser versionadas.
- O modelo pré-treinado InsightFace `buffalo_l` é licenciado para uso **não comercial**. Avalie a licença antes de qualquer uso comercial.

## Limitações conhecidas

- A logo remota original não está disponível; o cabeçalho usa o símbolo em `public/favicon.png` e o wordmark “LINS Agroindustrial”. Substitua pelo arquivo oficial quando disponível.
- O reconhecimento facial é auxiliar: condições de luz, enquadramento e cadastro influenciam a identificação, e o instrutor sempre pode usar o registro manual.
- A primeira inicialização com `FACE_MODEL_PRELOAD=true` pode demorar alguns segundos a mais enquanto o modelo é carregado em CPU.
- Os certificados são emitidos em PDF A4 com QR Code e download, mas não possuem assinatura digital ICP-Brasil ou carimbo de tempo.
- O QR Code usa `PUBLIC_BASE_URL` quando configurado; sem essa variável, ele aponta para o host usado na requisição. Para acesso pelo celular, configure o IP da LAN.
- O PDF é gerado sob demanda e não fica armazenado em disco; o código de verificação é a chave de autenticação pública.
- O envio real de e-mail depende de SMTP configurado; a demonstração padrão usa somente o outbox local.
- O outbox contém senhas temporárias em texto no banco local. Em produção, proteja o acesso ao RH, configure SMTP/HTTPS e avalie a política de retenção dessas mensagens.
- O fluxo foi validado em Windows e navegador Chromium, incluindo viewport de 390 px. O teste em Safari/iOS e com câmera física em HTTPS ainda deve ser feito manualmente.
- A interface e os textos podem evoluir em versões futuras.
- A documentação interativa em `/api/docs` carrega o Swagger UI via CDN (jsDelivr) somente quando `DEV_MODE=true`; ela precisa de internet. As rotas da API continuam funcionando offline.

## Solução de problemas

**Python não encontrado ou versão incompatível**

Instale o Python 3.12 em [python.org](https://www.python.org/downloads/windows/) e marque “Add python.exe to PATH”. Rode `setup.bat` novamente.

**Falha ao instalar InsightFace/ONNX Runtime**

Instale o “Build Tools for Visual Studio” com a carga “Desktop development with C++” e repita o setup.

**Node.js/npm não encontrado**

Instale Node.js 20 ou superior e rode `setup.bat` novamente.

**Porta 8000 em uso**

```bat
start.bat --port 8001
```

Para descobrir o processo que ocupa a porta:

```bat
netstat -ano | findstr :8000
taskkill /PID NUMERO_DO_PID /F
```

**Modelo facial ausente, download interrompido ou cadastro indisponível**

Remova `data/insightface/buffalo_l.zip` e execute:

```bat
venv\Scripts\python.exe scripts\download_model.py
```

Confirme que `data/insightface/models/buffalo_l` existe e que `FACE_MODEL_PRELOAD=true` está no `.env`. Para testar o modelo com as fotos locais:

```bat
venv\Scripts\python.exe scripts\check_face_model.py imagens_teste\pessoa2
```

**Frontend não compilado**

```bat
npm install
npm run build
```

Depois reinicie o servidor.

**Celular não acessa**

Confirme o IP, a rede Wi-Fi e a regra de firewall. Se a rede mudou, o endereço exibido pelo `start.bat` também muda.

O `start.bat` prioriza a rota padrão física (Wi-Fi/Ethernet) e ignora adaptadores virtuais conhecidos, como WSL, Hyper-V, VirtualBox e Cloudflare WARP. Se ainda houver dúvida, execute `ipconfig` e use o IPv4 do adaptador **Wi-Fi** ou **Ethernet** conectado à mesma rede do celular.

## Próximos passos

1. Validar o fluxo em Safari/iOS e em HTTPS com câmera física.
2. Configurar SMTP para envio real das mensagens do outbox.
3. Avaliar assinatura digital ICP-Brasil e carimbo de tempo para os certificados.
4. Preparar backup, monitoramento e política de retenção antes de uso em produção.
