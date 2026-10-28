# Yealink IP Phone pour Home Assistant

Intégration personnalisée pour les téléphones IP Yealink, développée pour le **SIP-T31W** (compatible T3x/T4x).

## Principe

| Canal | Rôle | Configuration téléphone |
|---|---|---|
| **Action URL** (le téléphone appelle Home Assistant) | état des appels, enregistrement SIP, DND, renvois, mute, attente, IP… en temps réel | *Features > Action URL* |
| **Action URI** (Home Assistant appelle le téléphone) | boutons, DND, service `yealink.dial` | *Security > Trusted IP > Action URI Allow IP List* = IP de HA |
| Ping HTTP toutes les 60 s | capteur « En ligne » | aucune |
| Statut web (option, **expérimental**) | firmware, MAC, uptime… | identifiants web |

## Installation

1. HACS > Dépôts personnalisés > ajouter ce dépôt (catégorie *Integration*), ou copier `custom_components/yealink` dans votre dossier `config`.
2. Redémarrer Home Assistant, puis *Paramètres > Appareils et services > Ajouter une intégration > Yealink IP Phone*.
3. Une notification contient toutes les lignes `action_url.*` à coller dans l'interface du téléphone (ou dans un fichier d'auto-provisioning). L'URL du webhook est aussi exposée par le capteur diagnostic « Action URL (webhook) ».

## Entités

**Capteurs** : état d'appel, enregistrement SIP, sens, numéro/nom distant, début d'appel, dernier appel entrant/sortant/manqué (numéro, nom, durée, heure), compteurs jour et total (entrants, sortants, décrochés, manqués), temps de conversation, compte et serveur SIP actifs, dernier événement, dernier démarrage, dernier changement d'IP, dernière activité, IP, MAC, modèle, firmware, matériel, uptime.

**Capteurs binaires** : en ligne, enregistré, sonnerie, en communication, décroché, micro coupé, en attente, ne pas déranger, renvois (inconditionnel / occupé / sans réponse).

**Boutons** : décrocher/OK, raccrocher, haut-parleur, casque, muet, attente, transfert, conférence, volume ±, bis, redémarrer. **Switch** : Ne pas déranger. **Entité événement** : un type par événement Action URL (utilisable en automatisation), plus un événement bus `yealink_event`.

**Service** `yealink.dial` (`device_id`, `number`).

## Exemple d'automatisation

```yaml
trigger:
  - platform: state
    entity_id: sensor.yealink_sip_t31w_call_state
    to: ringing
action:
  - service: notify.notify
    data:
      message: "Appel de {{ states('sensor.yealink_sip_t31w_current_remote_name') }}"
```

## Limites connues

- Les capteurs d'appel dépendent des événements envoyés par le téléphone : tant que l'Action URL n'est pas configurée, ils restent inconnus.
- Le statut web et les URI de composition (`key=number=`) ne sont pas documentés publiquement pour toutes les versions de firmware ; ils sont à valider sur votre téléphone.
- Cette version n'a pas encore été testée sur un vrai SIP-T31W ni dans un Home Assistant en fonctionnement.
