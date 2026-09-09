The conflict resolution is done in phases, called <math>K_n</math>. Each phase
is responsible for a type of conflicts.
Note that K0 -- for the simplest "conflicts" -- is the last phase to be evaluated:

 * k1 -- convoy conflicts (Aaa mve Zzz, Bbb con Aaa, Zzz hld). 
 * k2 -- simple conflicts (Aaa mve Zzz, Zzz hld).
 * k3 -- conflicts at border (Aaa mve Zzz, Zzz mve Aaa).
 * k4 -- chain of moves (Aaa mv Bbb, Bbb mve Ccc, Ccc mve Ddd), as well as circles of 3+.
 * k0 -- no conflict moves (Aaa mve Bbb).

((TODO: check with PJ if descriptions are correct))
