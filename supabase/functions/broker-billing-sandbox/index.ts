import {createHandler} from './core.mjs';
Deno.serve(createHandler({env:Deno.env.toObject()}));
