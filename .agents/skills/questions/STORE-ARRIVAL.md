# What the store holds before anything has happened in it

Machine input for the install, read by nobody at session time: a tree that has just received core
has a question store to work from and no question in it. The words
are kept here for every root until the mechanism that owns each root declares its own;
`questions.py --seed` writes them and the install only calls it.

Written only into a store that holds no entry, on an install or an update. From then on the roots
are the project's — nothing reseeds, rewords or removes them.

One root to a line, in the order they take their ids: the purpose, the structure, the landscape.

```roots
What is this project for?
How is this project built?
What landscape does this project evolve in?
```
