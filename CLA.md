# Umowa licencyjna kontrybutora (CLA)

> **SZABLON — WYMAGA PRZEJRZENIA PRZEZ PRAWNIKA PRZED UŻYCIEM.**
> To jest robocza wersja robocza oparta na powszechnie stosowanym wzorcu
> (Apache ICLA), przystosowana do modelu podwójnego licencjonowania.
> Zanim opublikujesz repozytorium, zleć jej weryfikację kancelarii IP —
> to zwykle jedna konsultacja, a od poprawności tego dokumentu zależy,
> czy w ogóle będziesz mógł sprzedawać licencje komercyjne.

## Dlaczego to jest potrzebne

wirewing jest udostępniany na dwóch ścieżkach: PolyForm Noncommercial dla
użytkowników niekomercyjnych i licencja komercyjna dla firm. Żeby udzielić
komuś licencji komercyjnej na fragment kodu, trzeba mieć do niego prawa.
Bez CLA każdy przyjęty pull request tworzy w projekcie kawałek, którego nie
wolno licencjonować komercyjnie — i cały model przestaje działać.

CLA **nie odbiera ci praw do twojego kodu**. Zachowujesz pełne prawa
autorskie i możesz ze swoim wkładem robić co chcesz, także wykorzystać go
gdzie indziej. Udzielasz jedynie dodatkowej licencji.

## Treść

Przesyłając wkład do projektu wirewing oświadczasz, że:

1. **Jesteś uprawniony.** Wkład jest twoim oryginalnym dziełem albo masz
   prawo go przekazać. Jeśli tworzysz go w ramach zatrudnienia, uzyskałeś
   zgodę pracodawcy albo pracodawca zrzekł się praw do tego wkładu.
   *(W Polsce istotne: art. 74 ust. 3 ustawy o prawie autorskim przyznaje
   majątkowe prawa autorskie do programu stworzonego w ramach obowiązków
   pracowniczych pracodawcy, o ile umowa nie stanowi inaczej.)*

2. **Udzielasz licencji autorskiej.** Udzielasz właścicielowi projektu
   wieczystej, ogólnoświatowej, niewyłącznej, nieodpłatnej i nieodwołalnej
   licencji na zwielokrotnianie, opracowywanie, publiczne udostępnianie,
   rozpowszechnianie i sublicencjonowanie twojego wkładu **na dowolnych
   warunkach licencyjnych, w tym komercyjnych**.

3. **Udzielasz licencji patentowej.** Na tych samych zasadach udzielasz
   licencji na patenty, które są niezbędne do korzystania z twojego wkładu,
   a które przysługują tobie lub które kontrolujesz.

4. **Nie dajesz gwarancji.** Wkład dostarczasz „tak jak jest", bez rękojmi
   ani gwarancji jakiegokolwiek rodzaju.

5. **Zgłaszasz cudzą własność.** Jeśli wkład zawiera fragmenty cudzego kodu,
   oznaczasz je i podajesz ich licencję. Kodu na licencji GPL lub LGPL
   linkowanego statycznie **nie przyjmujemy** — jest nie do pogodzenia
   z modelem licencjonowania tego projektu.

## Jak podpisać

Podpisanie odbywa się automatycznie przy pierwszym pull requeście — bot
[CLA Assistant](https://github.com/cla-assistant/cla-assistant) doda komentarz
z prośbą o potwierdzenie. Wystarczy odpowiedzieć jednym zdaniem, które poda.

Alternatywnie, dla drobnych poprawek (literówki, dokumentacja) akceptujemy
[Developer Certificate of Origin](https://developercertificate.org/) —
wystarczy `git commit -s`.
