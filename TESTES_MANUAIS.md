# Testes manuais — Marcos 1, 2, 3, 4, 5 e 6

Este roteiro valida a base local do Trilha de Talentos, a operação de RH/liderança, o cadastro facial, a chamada de presença, a certificação e o PDF: instalação, autenticação, troca de senha obrigatória, painéis por perfil, pessoas, treinamentos, reservas, outbox, consentimento LGPD, captura facial, reconhecimento, fallback manual, encerramento de turma, certificados, QR Code, download e acesso pelo celular.

**Escopo:** Marcos 1, 2, 3, 4, 5 e 6. A conclusão da turma emite certificados digitais verificáveis por código, com PDF e QR Code gerados sob demanda.

## Pré-requisitos

- Windows com Python 3.12 e Node.js 20+.
- Projeto instalado e servidor rodando com `start.bat`.
- Celular na mesma rede Wi-Fi do computador.
- Navegador atualizado no computador e no celular.

## Antes de começar

Se quiser repetir o teste de primeiro acesso, restaure os dados de demonstração. **Isso apaga o banco local.**

```powershell
# pare o servidor com Ctrl+C
Remove-Item data\app.db, data\app.db-wal, data\app.db-shm -ErrorAction SilentlyContinue
venv\Scripts\python.exe scripts\init_db.py
venv\Scripts\python.exe scripts\seed.py
start.bat
```

## 1. Instalação

- [x] Executar `setup.bat` (ou `setup.bat -Seed -NoHttps`) sem erros.
- [x] Confirmar mensagem `INSTALACAO CONCLUIDA`.
- [x] Confirmar que `.env` foi criado.
- [x] Confirmar que `data/app.db` existe.
- [x] Confirmar que `dist/index.html` existe.
- [x] Confirmar que o modelo está em `data/insightface/models/buffalo_l` (se não usou `-NoModel`).
- [x] Confirmar que o seed informa 3 treinamentos e 3 funcionários.

## 2. Inicialização

- [x] Executar `start.bat`.
- [x] Confirmar que o terminal mostra o endereço do computador e o endereço do celular.
- [x] Abrir `http://127.0.0.1:8000`.
- [x] Confirmar que a tela de login carrega com a logo, a paleta azul/verde e o texto “Capacitação que se comprova”.
- [x] Não deve haver seletor de perfil nem menu lateral.
- [x] Confirmar no terminal a mensagem `Modelo facial buffalo_l carregado (CPUExecutionProvider)`.
- [x] Confirmar que o primeiro start pode demorar alguns segundos a mais por causa do carregamento do modelo.

## 3. Login no computador

### RH

- [x] Entrar com `rh@lins.com.br` / `LinsRh@2026`.
- [x] Confirmar redirecionamento para `/rh`.
- [x] Confirmar título “Painel do RH”.
- [x] Confirmar indicadores de treinamentos, vagas, reservas e certificados.
- [x] Confirmar que “Pessoas”, “Treinamentos” e “Caixa de saída” abrem as telas de gestão do RH.
- [x] Abrir “Verificar certificado” e confirmar o retorno à tela pública.

### Líder

- [x] Sair pelo ícone no canto superior direito.
- [x] Entrar com `lider@lins.com.br` / `LinsLider@2026`.
- [x] Confirmar redirecionamento para `/lider`.
- [x] Confirmar “Minha equipe”, três pessoas e status “Face pendente”.
- [x] Confirmar três turmas com vagas.

### Instrutor

- [x] Sair e entrar com `instrutor@lins.com.br` / `LinsInstrutor@2026`.
- [x] Confirmar redirecionamento para `/instrutor`.
- [x] Confirmar “Minhas chamadas” e três turmas atribuídas.
- [x] Confirmar os cartões de presenças com valor zero.

### Funcionário

- [x] Sair e entrar com `joao@lins.com.br` / `Joao@2026`.
- [x] Confirmar redirecionamento para `/trocar-senha`.
- [x] Tentar acessar `/funcionario` diretamente antes da troca.
- [x] Confirmar que o sistema mantém o usuário em `/trocar-senha`.

## 4. Troca de senha

- [x] Preencher a senha atual `Joao@2026`.
- [x] Digitar uma nova senha sem número e confirmar que a regra permanece pendente.
- [x] Preencher uma nova senha válida, por exemplo `JoaoNovo@2026`.
- [x] Confirmar que os quatro requisitos ficam verdes.
- [x] Digitar uma confirmação diferente e confirmar a mensagem de erro.
- [x] Corrigir a confirmação e salvar.
- [x] Confirmar redirecionamento para `/funcionario`.
- [x] Confirmar que o convite de cadastro facial aparece no painel com o status pendente.
- [x] Confirmar que a senha temporária `Joao@2026` não funciona mais após logout.

## 5. Segurança e rotas

- [x] Sem sessão, acessar `/rh` diretamente; deve redirecionar para o login.
- [x] Sem sessão, acessar `/api/home`; deve retornar HTTP 401.
- [x] Como funcionário, acessar `/rh`; deve redirecionar para o painel de funcionário.
- [x] Fazer login com senha incorreta; deve retornar “E-mail ou senha inválidos”.
- [x] Fazer logout e confirmar que a sessão deixa de acessar o painel.
- [x] Abrir uma rota desconhecida, como `/pagina-inexistente`; deve aparecer a página 404 do sistema, sem quebrar o layout.
- [x] Abrir `http://127.0.0.1:8000/api/rota-inexistente`; deve retornar JSON 404.
- [x] Com `DEV_MODE=true`, abrir `/api/docs`; a documentação deve carregar o Swagger UI normalmente.
- [x] Confirmar no navegador que o cookie de sessão é `HttpOnly`.

## 6. Acesso pelo celular

- [x] Conectar o celular à mesma rede Wi-Fi.
- [x] Abrir o endereço `http://IP-DA-MAQUINA:8000` mostrado pelo `start.bat`; ele deve priorizar o IP físico da rede Wi-Fi/Ethernet (ex.: `192.168.68.150`).
- [x] Confirmar que a tela de login cabe na largura sem rolagem horizontal.
- [x] Fazer login com `beatriz@lins.com.br` / `Beatriz@2026`.
- [x] Confirmar a tela de troca de senha em tela pequena.
- [x] Confirmar que os campos e botões são fáceis de tocar.
- [x] Confirmar que o teclado não cobre permanentemente o botão principal.
- [x] Testar o botão “Voltar” e o ícone de sair.
- [ ] Se o acesso falhar, revisar a seção de firewall no README.

## 7. Verificação pública

- [x] Acessar `/verificar` sem estar logado.
- [x] Confirmar o cabeçalho “Verificação de certificado” e o botão de consulta.
- [x] Consultar um código inexistente, como `LINS-AAAAA-AAAAA-AAAAA`.
- [x] Confirmar a mensagem “Certificado não confirmado” e o HTTP 404 no fundo.
- [x] Confirmar que a página continua funcional e permite nova consulta.
- [ ] A consulta de um certificado válido será testada na seção 11, após o encerramento da turma.

## 8. Marco 2: pessoas, treinamentos, reservas e outbox

Os itens marcados `[x]` abaixo foram exercitados em banco isolado por uma validação E2E com Chromium, além dos testes Pytest. Os demais ficam para a rodada manual no banco principal.

### 8.1 Pessoas (RH)

- [x] Entrar como RH e abrir `Pessoas` pelo card de acesso rápido.
- [x] Cadastrar uma pessoa de teste como funcionária, vinculada a “Marcos Oliveira”.
- [x] Confirmar o modal “Senha temporária gerada”, com e-mail e senha de 10 caracteres.
- [x] Abrir `Caixa de saída`, buscar pelo e-mail criado e conferir a senha temporária no corpo da mensagem.
- [x] Editar o nome ou o líder de uma pessoa e confirmar a atualização na lista.
- [x] Usar “Nova senha” e confirmar que a senha anterior deixa de funcionar.
- [x] Tentar cadastrar um e-mail duplicado e confirmar a mensagem de erro.
- [x] Desativar a pessoa de teste e confirmar o selo “Inativo”.
- [x] Reativar a pessoa e confirmar que o login volta a funcionar.
- [x] Tentar desativar a própria conta de RH; o botão deve estar bloqueado ou a API deve recusar.
- [x] Tentar desativar o único RH ativo em outra sessão; a API deve retornar erro.

### 8.2 Treinamentos (RH)

- [x] Abrir `Treinamentos` pelo card de acesso rápido.
- [x] Criar a turma “Teste E2E”, com instrutor, data futura, local, horário, vagas e carga horária.
- [x] Confirmar a turma na lista, com progresso de vagas e status “Agendado”.
- [x] Excluir a turma sem reservas e confirmar o feedback de exclusão.
- [x] Editar uma turma e confirmar que data, local e vagas são atualizados.
- [x] Cancelar uma turma com reservas e confirmar que as reservas ativas também são canceladas.
- [x] Tentar criar turma com data passada e confirmar o erro.
- [x] Tentar criar turma com término anterior ao início e confirmar o erro.
- [x] Reduzir as vagas abaixo das reservas ativas e confirmar o bloqueio.

### 8.3 Reservas do líder

- [x] Sair e entrar como líder; abrir “Gerenciar reservas”.
- [x] Reservar uma vaga na turma “Boas Práticas de Fabricação” para a pessoa criada pelo RH.
- [x] Confirmar o feedback de 1 reserva, o incremento da turma e o card em “Reservas do time”.
- [x] Cancelar a reserva e confirmar a devolução da vaga.
- [x] Selecionar mais pessoas do que as vagas disponíveis e confirmar o limite.
- [x] Confirmar que pessoa já reservada aparece desabilitada e não pode ser duplicada.
- [x] Como líder, tentar abrir `/rh/pessoas`; deve redirecionar para `/lider`.
- [x] Sair e confirmar que `/lider/reservas` sem sessão redireciona para o login.

### 8.4 Outbox e responsividade

- [x] Buscar mensagens por destinatário no outbox.
- [x] Abrir os detalhes de uma mensagem e conferir assunto, destinatário, corpo e status “Registrado”.
- [x] Usar “Copiar mensagem” e confirmar o feedback “Copiado”.
- [x] Confirmar que `/rh/pessoas`, `/rh/trainings` e `/rh/outbox` não têm rolagem horizontal em 390 px.
- [x] Confirmar o mesmo para `/lider/reservas` em 390 px.
- [x] Repetir o fluxo de reserva em um celular físico na mesma rede Wi-Fi.

### 8.5 SMTP opcional

- [ ] Sem `SMTP_HOST`, confirmar que as mensagens ficam no outbox e nenhum e-mail real é enviado.
- [ ] Com um SMTP de teste configurado, confirmar que a mensagem é registrada e o status de envio é atualizado.

## 9. Marco 3: consentimento e cadastro facial

Os itens marcados `[x]` foram exercitados em banco isolado por uma validação E2E com Chromium. A câmera foi simulada; o upload de arquivo foi o caminho usado para concluir as capturas. A câmera física e o HTTPS em celular continuam pendentes de teste manual.

### 9.1 Consentimento

- [x] Entrar como funcionário com a senha já alterada e abrir `/cadastro-facial`.
- [x] Confirmar o título, o resumo e as seções do termo LGPD versão 1.0.
- [x] Tentar capturar sem marcar o aceite e confirmar que o fluxo permanece bloqueado.
- [x] Marcar o aceite e confirmar que a etapa de captura é liberada.
- [x] Recarregar a página e confirmar que o consentimento continua registrado.
- [x] Confirmar em `/api/face/status` que `consent.current_version`, `accepted` e `needs_acceptance` refletem o estado correto.

### 9.2 Capturas e qualidade

- [x] Tirar ou enviar uma primeira foto com um único rosto bem iluminado.
- [x] Confirmar o progresso `1 de 3`, o feedback de captura e o botão para refazer.
- [x] Enviar uma foto de outra pessoa e confirmar a recusa por inconsistência, sem aumentar o progresso.
- [x] Confirmar que a mensagem orienta usar fotos da mesma pessoa e manter boa iluminação.
- [ ] Enviar arquivo acima de 8 MB ou com formato não suportado e confirmar o erro.
- [x] Enviar imagem sem rosto, com mais de um rosto ou com rosto muito pequeno e confirmar a recusa.
- [x] Completar as três capturas e confirmar a tela de sucesso.
- [x] Confirmar no painel que o status facial passa a “Cadastro ativo”.
- [x] Confirmar que uma quarta captura é recusada pela API.

### 9.3 Refazer, persistência e revogação

- [x] Abrir “Refazer cadastro” e confirmar que as capturas são apagadas, mas o consentimento permanece.
- [x] Repetir as três capturas e concluir novamente.
- [x] Recarregar a página e confirmar que o cadastro permanece ativo.
- [x] Abrir “Revogar consentimento”, confirmar o diálogo de aviso e concluir.
- [x] Confirmar que o status volta para pendente e que as capturas desaparecem.
- [x] Confirmar via `/api/face/status` que há zero amostras e que o consentimento não está aceito.
- [x] Confirmar que a ação de revogação aparece na auditoria do sistema.

### 9.4 Câmera, upload e responsividade

- [x] Com a câmera simulada, confirmar o preview, a guia facial e o botão de captura.
- [x] Confirmar que o upload alternativo funciona quando a câmera não está disponível.
- [x] Confirmar que `/cadastro-facial` não tem rolagem horizontal em 390 px.
- [x] Confirmar que os textos e botões principais cabem na tela pequena.
- [ ] Em celular físico, abrir via HTTPS, permitir a câmera e concluir as três capturas.
- [ ] Repetir a revogação em celular e confirmar o layout do diálogo.

### 9.5 Modelo e privacidade

- [x] Executar `venv\Scripts\python.exe scripts\check_face_model.py imagens_teste\pessoa2`.
- [x] Confirmar que todas as fotos são detectadas e que a menor similaridade fica acima de `0.30`.
- [x] Confirmar que nenhuma imagem original é enviada ao banco ou gravada em `data/`.
- [x] Confirmar que, após a revogação, não restam vetores faciais para o usuário.

## 10. Marco 4: chamada e presença

Os itens marcados `[x]` foram exercitados em banco isolado por uma validação E2E com Chromium. A turma NR-12 foi ajustada para a data atual, o funcionário Rafael recebeu três vetores de `imagens_teste/pessoa2` e a câmera foi simulada; o upload foi o caminho usado para o reconhecimento real. A câmera física em celular/HTTPS continua pendente de teste manual.

### 10.1 Acesso e estado da chamada

- [x] Entrar como instrutor e confirmar as três turmas atribuídas.
- [x] Confirmar o botão **Abrir chamada** em cada turma.
- [x] Abrir a turma NR-12 e confirmar título, status, data, local, instrutor, resumo e participantes.
- [x] Confirmar a lista de pendentes com os selos **Face ativa** e **Sem cadastro facial**.
- [x] Abrir uma turma sem reservas e confirmar **Chamada indisponível**, sem botões de câmera ou upload.
- [x] Confirmar que turma cancelada ou concluída também bloqueia a chamada (coberto pelos testes de API).
- [x] Abrir `/instrutor/chamadas/abc` e confirmar a página 404.
- [x] Como funcionário, tentar abrir `/instrutor/chamadas/1` e confirmar o redirecionamento para `/funcionario`.

### 10.2 Reconhecimento facial

- [x] Abrir a chamada da NR-12 e confirmar `0 de 2` presenças, dois pendentes e um rosto cadastrado.
- [x] Ativar a câmera simulada e confirmar preview e botão **Registrar presença**.
- [x] Enviar uma foto de `imagens_teste/pessoa3` e confirmar **Presença não confirmada**, sem alterar o resumo.
- [x] Confirmar a orientação para usar o registro manual como fallback.
- [x] Enviar uma foto de `imagens_teste/pessoa2` e confirmar a presença de Rafael Souza com similaridade.
- [x] Confirmar a atualização para `1 de 2` presenças e `1 pendente`.
- [ ] Repetir a foto de Rafael e confirmar que a presença é idempotente (coberto pelos testes de API).
- [ ] Testar ambigüidade entre duas pessoas cadastradas e confirmar a orientação para registro manual (coberto pelos testes de API).
- [ ] Enviar imagem sem rosto, com mais de um rosto ou acima de 8 MB e confirmar a recusa.

### 10.3 Fallback manual

- [x] Clicar em **Registrar** ao lado de Beatriz Lima e confirmar a identificação no diálogo.
- [x] Confirmar que o botão **Confirmar presença** começa desabilitado com justificativa vazia.
- [x] Preencher uma justificativa e concluir o registro manual.
- [x] Confirmar `2 de 2` presenças, `1 facial`, `1 manual` e o estado **Chamada completa**.
- [x] Confirmar na lista de presenças o selo **Manual**, o horário e a justificativa.
- [x] Tentar registrar manualmente uma pessoa fora da reserva e confirmar o erro (coberto pelos testes de API).
- [x] Tentar registrar manualmente a mesma pessoa duas vezes e confirmar o conflito (coberto pelos testes de API).

### 10.4 Remoção e privacidade

- [x] Remover a presença de Rafael Souza e confirmar o diálogo de aviso.
- [x] Confirmar que Rafael volta aos pendentes, com `1 de 2` presenças.
- [x] Confirmar que a remoção atualiza os contadores facial/manual.
- [x] Confirmar que a rota de chamada não tem rolagem horizontal em 390 px.
- [ ] Confirmar que remover presença de turma concluída é bloqueado (coberto pelos testes de API).
- [x] Confirmar que nenhuma foto original foi criada em `data/` após os testes de chamada.
- [ ] Em celular físico, abrir via HTTPS, permitir a câmera e registrar uma presença facial.

### 10.5 Modelo, API e auditoria

- [x] Confirmar o preload do modelo `buffalo_l` no log do servidor.
- [x] Confirmar no resumo da API os valores `reserved`, `present`, `pending`, `face` e `manual`.
- [x] Confirmar que a chamada de hoje retorna `is_today=true` e `can_record=true`.
- [x] Confirmar na auditoria os eventos de presença facial, manual e remoção.
- [ ] Reiniciar o servidor e confirmar que as presenças permanecem no banco isolado.

## 11. Marco 5: encerramento e certificados

Execute preferencialmente em banco isolado para não alterar a turma de demonstração do banco principal. Os itens marcados `[x]` foram cobertos pelo E2E com Chromium em banco isolado ou pelos testes Pytest.

- [x] Entrar como instrutor e abrir a chamada da turma NR-12.
- [x] Registrar a presença de Rafael e deixar Beatriz pendente.
- [x] Confirmar o card **Concluir e emitir certificados** com `1 participante com presença registrada receberá certificado`.
- [x] Clicar em **Encerrar turma** e conferir o diálogo com `Será emitido 1 certificado` e o aviso de que Beatriz ficará sem certificado.
- [x] Confirmar o encerramento e verificar o badge **Encerrada**, o total de certificados e a data de conclusão.
- [x] Abrir o link do certificado na lista de presenças e conferir o código `LINS-XXXXX-XXXXX-XXXXX`.
- [x] Consultar o código em `/verificar` sem login e confirmar nome, treinamento, carga horária, data e código.
- [x] Entrar como Rafael e confirmar o certificado no painel do funcionário.
- [x] Tentar registrar presença de Beatriz e confirmar o bloqueio por turma concluída.
- [x] Entrar como líder e tentar cancelar a reserva de Beatriz; confirmar o bloqueio.
- [x] Conferir no outbox do RH a mensagem `Certificado emitido: ...` com o código e o link de verificação.
- [x] Conferir na auditoria os eventos `treinamento_concluido` e `certificado_emitido`.
- [x] Em uma turma sem presenças, confirmar que o encerramento é permitido, mas emite `0` certificados com aviso (coberto por Pytest).
- [ ] Confirmar que o card de encerramento e o diálogo não têm overflow em 390 px.

## 12. Marco 6: PDF, QR Code e carga

Execute com um certificado emitido em banco isolado ou no banco principal. Os itens marcados `[x]` foram cobertos pelo E2E com Chromium, pelos testes Pytest ou pelo teste de carga local.

- [x] Abrir `/verificar/{codigo}` sem login e confirmar nome, treinamento, carga horária, data e código.
- [x] Confirmar que o QR Code aparece carregado na página pública.
- [x] Baixar o PDF pelo botão **Baixar PDF** e confirmar o arquivo `certificado-{codigo}.pdf`.
- [x] Confirmar que o PDF abre em uma página A4 paisagem, com logo, dados do certificado, assinatura, código e QR.
- [x] Entrar como o funcionário, abrir **Meus certificados** e baixar o PDF pelo atalho **PDF**.
- [x] Clicar em **Abrir** no certificado do funcionário e confirmar a verificação pública.
- [x] Confirmar que a verificação e o PDF funcionam sem sessão autenticada.
- [x] Conferir no outbox do RH o e-mail de certificado com o link direto do PDF.
- [x] Solicitar PDF ou QR de código inexistente e confirmar `404`.
- [ ] Ler o QR com a câmera de um celular na mesma rede e confirmar a abertura da URL pública (requer `PUBLIC_BASE_URL` com o IP da LAN).
- [x] Confirmar o layout da página pública e do botão de download em 390 px sem overflow.
- [x] Executar o teste de carga local:

```bat
venv\Scripts\python.exe scripts\load_test.py --base-url http://127.0.0.1:8001 --code LINS-XXXXX-XXXXX-XXXXX --endpoint mixed --requests 120 --concurrency 12
```

Referência da validação local: `120/120` requisições com sucesso, `0` falhas, cerca de `79 req/s`, p95 de aproximadamente `199 ms` em banco isolado.

## 13. Testes automatizados e build

Executar:

```bat
venv\Scripts\python.exe -m pytest
npm run typecheck
npm run lint
npm run build
```

- [x] `pytest` termina com `35 passed`.
- [x] TypeScript termina sem erros.
- [x] ESLint termina sem erros.
- [x] Build do Vite termina com sucesso.

## 14. Encerramento

- [x] Encerrar o servidor com `Ctrl+C`.
- [x] Confirmar que a porta 8000 foi liberada.
- [ ] Registrar capturas de tela (opcional) em uma pasta local não versionada.

## Critérios de aceite do Marco 1

- Instalação reproduzível em Windows.
- Login e logout funcionando para os quatro perfis.
- Redirecionamento por papel e proteção de rotas.
- Troca de senha obrigatória funcional.
- Layout mobile-first sem overflow em 390 px.
- Acesso pelo celular na rede local.
- Testes automatizados verdes.
- Nenhuma funcionalidade de marcos futuros apresentada como concluída.
- Nenhum dado sensível ou segredo versionado.

## Critérios de aceite do Marco 2

- RH consegue cadastrar, editar, ativar/desativar e resetar a senha de pessoas com as regras de vínculo e proteção.
- RH consegue criar, editar, cancelar e excluir treinamentos quando permitido.
- Líder consegue reservar e cancelar vagas somente para a própria equipe.
- Capacidade, duplicidade e estados de treinamento são validados no backend.
- Credenciais temporárias e notificações aparecem no outbox restrito ao RH.
- Ações de RH e líder estão integradas ao roteador com guards por papel.
- Layout validado em 390 px sem overflow horizontal.
- Testes Pytest, typecheck, lint e build verdes.

## Critérios de aceite do Marco 3

- O termo LGPD é versionado, exibido antes das capturas e exige aceite explícito.
- O cadastro facial coleta três amostras, valida um único rosto e recusa capturas inconsistentes.
- As fotos originais não são persistidas; somente vetores faciais e metadados são armazenados.
- O cadastro pode ser refeito sem perder o consentimento.
- A revogação exclui consentimento e vetores, desativa o status facial e registra auditoria.
- O modelo é carregado localmente em CPU e o servidor informa falhas de disponibilidade com segurança.
- O fluxo com câmera/upload funciona em 390 px sem overflow horizontal.
- Testes Pytest, typecheck, lint e build verdes.

## Critérios de aceite do Marco 4

- O instrutor acessa somente as próprias turmas e vê participantes, presenças e resumo.
- A chamada é bloqueada em turma cancelada, concluída ou sem reservas ativas.
- O reconhecimento facial considera somente participantes com reserva ativa e cadastro facial.
- Limiar e margem evitam confirmações ambíguas; falhas orientam o fallback manual.
- O registro manual exige justificativa, valida a reserva e não depende de biometria.
- Presenças faciais duplicadas são idempotentes e registros manuais duplicados são recusados.
- A remoção atualiza o resumo e é bloqueada em turma concluída.
- A chamada funciona em 390 px sem overflow e as rotas têm guards por papel.
- Testes Pytest, typecheck, lint, build e E2E em Chromium verdes.

## Critérios de aceite do Marco 5

- Somente o instrutor responsável encerra a turma, com CSRF e ownership validados no backend.
- O encerramento é bloqueado para turma cancelada, já concluída ou sem reservas ativas.
- Apenas participantes com reserva ativa e presença recebem certificado; pendentes não bloqueiam o encerramento.
- Turma sem presenças pode ser encerrada com zero certificados e aviso explícito.
- Cada certificado tem código único no formato `LINS-XXXXX-XXXXX-XXXXX` e um registro por treinamento/funcionário.
- A página pública confirma o certificado sem exigir login.
- O certificado aparece no painel do funcionário e no resumo do instrutor.
- Após a conclusão, presenças e reservas da turma ficam imutáveis.
- O outbox e a auditoria registram a emissão dos certificados.
- Testes Pytest, typecheck, lint, build e E2E em Chromium verdes.

## Critérios de aceite do Marco 6

- O certificado pode ser baixado em PDF A4, em uma única página, com os dados corretos e identidade visual.
- O PDF é público pelo código, tem nome de arquivo `certificado-{codigo}.pdf` e MIME `application/pdf`.
- O QR Code é público em PNG, abre a URL `/verificar/{codigo}` e é legível por leitor de QR.
- O painel do funcionário oferece download direto e abertura da verificação pública.
- O e-mail de emissão contém o link do PDF.
- Código inexistente retorna `404` para PDF e QR.
- A geração é local, sem serviço externo, e não exige persistência do arquivo PDF.
- O teste de carga executado no ambiente local termina sem falhas e registra p50/p95/p99.
- Testes Pytest, typecheck, lint, build e E2E em Chromium verdes.

## Problemas conhecidos e esperados

- A logo é composta pelo favicon e pelo wordmark, pois o arquivo original completo não está disponível.
- O modelo facial é carregado no primeiro start e pode acrescentar alguns segundos ao tempo de inicialização.
- O reconhecimento facial depende de iluminação, enquadramento e cadastro; o registro manual permanece disponível.
- Os certificados são emitidos em PDF com QR Code, mas não possuem assinatura digital ICP-Brasil ou carimbo de tempo.
- O QR Code aponta para o host da requisição quando `PUBLIC_BASE_URL` não está configurado; para leitura no celular, use o IP da LAN nessa variável.
- O PDF é gerado sob demanda e não fica armazenado em disco.
- Sem SMTP configurado, as mensagens ficam somente no outbox local; o envio real é opcional no Marco 2.
- O outbox contém senhas temporárias em texto no banco de desenvolvimento.
- O certificado HTTPS autoassinado pode gerar aviso no celular.
- Fotos de teste não são versionadas.
- A câmera física em celular e o comportamento em Safari/iOS ainda precisam de validação manual.

## Correções aplicadas após a primeira rodada

- **`/api/docs` em branco:** a CSP bloqueava os arquivos do Swagger UI no CDN. O CSP agora libera o jsDelivr somente com `DEV_MODE=true`. Reteste o item correspondente na seção 5.
- **IP incorreto no `start.bat`:** havia um adaptador virtual (Cloudflare WARP) sendo escolhido. O script agora prioriza a rota física Wi-Fi/Ethernet e ignora adaptadores virtuais conhecidos. Reteste o item correspondente na seção 6.
- **Testes automatizados:** a suíte agora termina com `35 passed`, incluindo encerramento, certificação, PDF, QR Code e regressão dos avisos plurais do Marco 5.
- **Marco 6:** PDF público e do painel, QR Code PNG, verificação sem sessão, 404, link no outbox, download real em Chromium e layout de 390 px foram validados em banco isolado. O teste de carga local concluiu `120/120` requisições sem falhas (`~79 req/s`, p95 `~199 ms`).
- **Marco 2:** as rotas `/rh/pessoas`, `/rh/trainings`, `/rh/outbox` e `/lider/reservas` foram conectadas aos guards e títulos da SPA. A validação E2E em Chromium confirmou criação/reset de pessoa, treinamento, reserva/cancelamento e outbox.
- **Marco 3:** consentimento, captura guiada, upload alternativo, reset de capturas e revogação foram validados em E2E com Chromium e banco isolado. O horário do aceite passou a ser serializado em UTC com sufixo `Z` para exibir corretamente no fuso local.
- **Marco 4:** chamada, bloqueio de turma vazia, reconhecimento de `pessoa2`, recusa de `pessoa3`, fallback manual, remoção, 404, guard de funcionário e layout de 390 px foram validados em E2E com Chromium e banco isolado. A interface também foi corrigida para não exibir controles de câmera em chamadas bloqueadas.
- **Preview da câmera preto:** o stream era anexado ao `<video>` antes de o elemento existir na chamada. O preview agora recebe o stream após a renderização; cadastro facial e chamada foram validados com frames reais `1280x960` (`readyState=4`).
- **Marco 5:** encerramento com um presente e um pendente, emissão de certificado único, verificação pública, painel do funcionário, bloqueio de cancelamento pelo líder, outbox, auditoria e layout de 390 px foram validados em E2E com Chromium e banco isolado.
