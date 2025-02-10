// inputs: :x, :y, :z

:t = :x + :y + :z
:s = :y + :t + :x


assert (:x + 100 < :y) && (:x + 200 > :y) && !(:x >= 0) && (:x * :y < -:x) && (:t > 0)