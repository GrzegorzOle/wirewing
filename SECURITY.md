# Polityka bezpieczeństwa

## Zgłaszanie podatności

**Nie otwieraj publicznego issue.**

Napisz na **oleksy@cdest.eu** z tematem `[SECURITY] wirewing`. Potwierdzę
przyjęcie w ciągu 3 dni roboczych i będę informował o postępach co najmniej
raz na 2 tygodnie.

Możesz też użyć prywatnego zgłaszania podatności na GitHubie
(zakładka *Security* → *Report a vulnerability*).

Przydatne w zgłoszeniu: wersja wirewing, model urządzenia, opis scenariusza
ataku i minimalny sposób odtworzenia. Jeśli chcesz, żeby cię wymienić w
podziękowaniach — napisz, pod jaką nazwą.

## Zakres

**W zakresie:** przepełnienia i wyczerpanie pamięci w parserze ramek, błędy
w walidacji sum kontrolnych umożliwiające wstrzyknięcie komendy, podatności
umożliwiające przejęcie sterowania przez łącze, wykonanie kodu przy
przetwarzaniu danych z portu.

**Poza zakresem:** brak szyfrowania i uwierzytelnienia na łączu RS-232 — to
cecha warstwy fizycznej, nie błąd. Kto ma dostęp do przewodu, ma dostęp do
urządzenia. Jeśli twój scenariusz zagrożeń tego nie dopuszcza, potrzebujesz
warstwy kryptograficznej nad transportem; napisz, jeśli chcesz o tym pogadać.

Poza zakresem są też błędy w firmware urządzeń — zgłoś je producentowi.

## Wersje wspierane

Poprawki bezpieczeństwa trafiają do najnowszego wydania z linii `0.x`.
Po wydaniu `1.0` wsparcie obejmie bieżącą wersję minor i poprzednią.

## Kontekst bezpieczeństwa operacyjnego

wirewing steruje latającą maszyną. Błąd w tym kodzie może oznaczać upadek
drona, a nie tylko wywrócony proces. Dlatego:

- traktuję zawieszenie parsera i zgubienie ramki jako błąd bezpieczeństwa,
  a nie zwykły defekt;
- wątek odbiorczy nie może paść na wyjątku z callbacku użytkownika;
- brak potwierdzenia musi kończyć się jawnym wyjątkiem, nigdy cichym pominięciem.

Jeśli zauważysz miejsce, gdzie któraś z tych zasad jest złamana — to jest
zgłoszenie bezpieczeństwa.
