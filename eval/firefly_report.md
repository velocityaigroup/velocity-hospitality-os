# Firefly Estate Bequia — SOP Coach evaluation (38 cases)

- Corpus: **24 records** across **9 departments**, **11 declared knowledge gaps**
- Operator-confirmed records: **0 of 24** — this is a public-source seed, not confirmed content
- Retrieval@1 on documented questions: **100%**
- Declared-gap refusal (refused AND named the right gap): **100%**
- Out-of-scope refusal: **100%**
- Overall correct: **100%**

| | Question | Expected | Got |
|---|---|---|---|
| ✅ | how much is the estate tour? | FF-503 | FF-503 |
| ✅ | what day does the plantation tour not run? | FF-503 | FF-503 |
| ✅ | what is the private tour price? | FF-504 | FF-504 |
| ✅ | how much does golf cost and are clubs included? | FF-501 | FF-501 |
| ✅ | is croquet free? | FF-502 | FF-502 |
| ✅ | who runs the diving? | FF-505 | FF-505 |
| ✅ | is breakfast included? | FF-205 | FF-205 |
| ✅ | is laundry included in the room? | FF-205 | FF-205 |
| ✅ | do you cater for special diets? | FF-402 | FF-402 |
| ✅ | can non residents eat at the restaurant? | FF-401 | FF-401 |
| ✅ | how much deposit do I pay when booking? | FF-301 | FF-301 |
| ✅ | can I cancel and get a refund? | FF-302 | FF-302 |
| ✅ | what happens if I arrive late? | FF-302 | FF-302 |
| ✅ | which credit cards do you accept? | FF-303 | FF-303 |
| ✅ | is tipping expected? | FF-605 | FF-605 |
| ✅ | is there a ferry from Barbados? | FF-604 | FF-604 |
| ✅ | where is the hotel and how far is the dock? | FF-101 | FF-101 |
| ✅ | how old is the sugar mill? | FF-102 | FF-102 |
| ✅ | which rooms are on the upper floor? | FF-201 | FF-201 |
| ✅ | is there wifi in the rooms? | FF-603 | FF-603 |
| ✅ | what sockets do you use, do I need an adaptor? | FF-603 | FF-603 |
| ✅ | are there mosquitoes or malaria? | FF-602 | FF-602 |
| ✅ | are there dogs on the property? | FF-602 | FF-602 |
| ✅ | tell me about the beach and sand flies | FF-601 | FF-601 |
| ✅ | does the villa have a private pool? | FF-204 | FF-204 |
| ✅ | does the estate cottage suit a family with children? | FF-203 | FF-203 |
| ✅ | what is the number to book a table? | FF-701 | FF-701 |
| ✅ | how should our messages to guests sound? | FF-901 | FF-901 |
| ✅ | what is the room rate for a week in March? | G1 | G1 |
| ✅ | how much is the villa per night? | G1 | G1 |
| ✅ | what time is dinner served? | G2 | G2 |
| ✅ | what time can I check in? | G3 | G3 |
| ✅ | how much is a taxi from the airport? | G4 | G4 |
| ✅ | what is your tripadvisor rating? | G9 | G9 |
| ✅ | what is the capital of France? | refuse | REFUSED |
| ✅ | tell me a joke about penguins | refuse | REFUSED |
| ✅ | what's the weather forecast tomorrow? | refuse | REFUSED |
| ✅ | how do I reset my email password? | refuse | REFUSED |

_Run with `python eval/firefly_eval.py`. The authored demo corpus is evaluated separately by `eval/run_eval.py`; the two corpora are never mixed._