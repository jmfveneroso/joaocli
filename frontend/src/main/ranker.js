import API from './api.js';
import {Vector, Physics} from './physics.js';

class TrieNode {
  constructor() {
    this.chars = {} 
    let leaf = false
  }
}

class Ranker {
  constructor(nodes) {
    this.vocab = {} 
    this.trie = new TrieNode()
  }

  tokenize(str) {
    const url_pattern = /http[s]?:\/\/(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+/
    const separator_pattern = /\s+|[:=(),.'?]/

    let good_tkns = []
    const tkns = str.split(/\s+/)
    for (let i = 0; i < tkns.length; i++) {
      if (tkns[i].match(url_pattern)) {
        good_tkns.push(tkns[i])
      } else {
        let ltkn = tkns[i].toLowerCase()
        good_tkns = good_tkns.concat(ltkn.split(separator_pattern))
      }
    }
    return good_tkns.filter(t => t.length > 0)
  }

  createVocab(entries) {
    this.vocab = {}
    for (let i = 0; i < entries.length; i++) {
      let tokens = this.tokenize(entries[i].title + entries[i].content)

      for (let j = 0; j < tokens.length; j++) {
        if (this.vocab[tokens[j]] === undefined) this.vocab[tokens[j]] = 0
        this.vocab[tokens[j]]++
      }
    }
    this.createTrie()
  }

  createTrie() {
    for (let t in this.vocab) {
      let current_node = this.trie
      for (let i = 0; i < t.length; i++) {
        let c = t.charAt(i)
        if (!current_node.chars.hasOwnProperty(c)) {
          current_node.chars[c] = new TrieNode()
        }
        current_node = current_node.chars[c]
      }
      current_node.leaf = true
    }
  }

  getTokensFromPrefixInternal(trie_node, prefix) {
    let tokens = (trie_node.leaf) ? [prefix] : []
    for (let c in trie_node.chars) {
      tokens = tokens.concat(this.getTokensFromPrefixInternal(trie_node.chars[c], prefix + c))
    }
    return tokens
  }

  getTokensFromPrefix(prefix) {
    let tokens = []
    if (prefix.length < 3) return tokens

    let current_node = this.trie
    for (let i = 0; i < prefix.length; i++) {
      let c = prefix.charAt(i)
      if (!current_node.chars.hasOwnProperty(c)) return []
      current_node = current_node.chars[c]
    }
    return this.getTokensFromPrefixInternal(current_node, prefix)
  }

  scoreEntries(query, entries) {
    let query_tokens = []
    let tmp = this.tokenize(query)
    for (let i = 0; i < tmp.length; i++) {
      query_tokens = query_tokens.concat(this.getTokensFromPrefix(tmp[i]))
    }
    for (let i = 0; i < entries.length; i++) {
      let score = 0
      let norm = 0
      let tokens = this.tokenize(entries[i].title + entries[i].content)
      for (let j = 0; j < tokens.length; j++) {
        let tkn_count = this.vocab[tokens[j]]
        if (tkn_count === undefined) continue

        if (query_tokens.includes(tokens[j])) {
          score += Math.pow(1.0 / tkn_count, 2)
        }
        norm += Math.pow(1.0 / tkn_count, 2)
      }

      if (norm > 0) score /= Math.sqrt(norm)
      entries[i].score = score
    }
  }
}

let RankerSingleton = new Ranker()
export default RankerSingleton;
