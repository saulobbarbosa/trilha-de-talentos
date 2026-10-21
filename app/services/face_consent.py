from __future__ import annotations

FACE_CONSENT_VERSION = "1.0"
FACE_CONSENT_UPDATED_AT = "2026-10-21"
FACE_CONSENT_TITLE = "Termo de consentimento para tratamento de dados biométricos faciais"

FACE_CONSENT_SECTIONS = [
    {
        "heading": "1. Controlador e canal de privacidade",
        "body": (
            "A Lins Agroindustrial, por meio da área de Recursos Humanos/Universidade Lins, "
            "é responsável pelo tratamento dos dados informados neste termo. Dúvidas e solicitações "
            "podem ser encaminhadas ao RH ou ao canal de Privacidade da empresa."
        ),
    },
    {
        "heading": "2. Finalidade do tratamento",
        "body": (
            "Os dados biométricos serão usados exclusivamente para cadastrar e reconhecer você "
            "na conferência de presença dos treinamentos, ajudando a evitar identificações "
            "incorretas e registros de presença por outra pessoa."
        ),
    },
    {
        "heading": "3. Quais dados são tratados",
        "body": (
            "As fotos enviadas são processadas no servidor local para detectar o rosto e gerar "
            "um modelo matemático (vetor biométrico). As imagens originais não são armazenadas. "
            "O sistema guarda até três vetores faciais, o nome do modelo utilizado e o registro "
            "do consentimento com data, hora e endereço IP. O vetor biométrico é um dado pessoal "
            "sensível e não permite reconstruir a foto original."
        ),
    },
    {
        "heading": "4. Base legal e voluntariedade",
        "body": (
            "O tratamento ocorre com base no seu consentimento, nos termos do art. 7º, inciso I, "
            "e do art. 11, inciso I, da LGPD. O cadastro é opcional: a recusa ou a revogação não "
            "impede a inscrição em treinamentos. Nesses casos, a presença poderá ser registrada "
            "manualmente pelo instrutor."
        ),
    },
    {
        "heading": "5. Armazenamento, acesso e prazo",
        "body": (
            "Os vetores ficam em infraestrutura local da empresa, com acesso restrito a pessoas "
            "autorizadas e registro de operações de auditoria. Os dados são mantidos enquanto o "
            "consentimento estiver válido e a conta estiver ativa. Ao revogar o consentimento, "
            "os vetores faciais são excluídos imediatamente e o registro do cadastro é desativado."
        ),
    },
    {
        "heading": "6. Compartilhamento",
        "body": (
            "Os dados não são vendidos nem compartilhados com terceiros para publicidade. O "
            "processamento facial ocorre localmente, sem envio das imagens ou dos vetores para "
            "serviços de nuvem. Informações poderão ser fornecidas apenas quando houver obrigação "
            "legal ou ordem de autoridade competente."
        ),
    },
    {
        "heading": "7. Seus direitos",
        "body": (
            "Você pode solicitar confirmação do tratamento, acesso, correção, anonimização, "
            "bloqueio ou eliminação dos dados, portabilidade quando aplicável, informação sobre "
            "compartilhamento e revogação do consentimento. A revogação pode ser feita nesta mesma "
            "tela, a qualquer momento, sem necessidade de justificativa."
        ),
    },
    {
        "heading": "8. Segurança e atualizações",
        "body": (
            "O sistema utiliza sessão autenticada, proteção contra requisições indevidas, controle "
            "de acesso e trilha de auditoria. Se este termo mudar, uma nova versão será apresentada "
            "e um novo consentimento será solicitado antes de qualquer nova captura."
        ),
    },
]


def consent_term_payload() -> dict:
    return {
        "version": FACE_CONSENT_VERSION,
        "updated_at": FACE_CONSENT_UPDATED_AT,
        "title": FACE_CONSENT_TITLE,
        "summary": (
            "Autorizo o uso do meu modelo facial exclusivamente para conferência de presença "
            "nos treinamentos. O cadastro é opcional e posso revogar o consentimento quando quiser."
        ),
        "sections": FACE_CONSENT_SECTIONS,
    }
