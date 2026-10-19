import {it,expect} from 'vitest';
import {programmeKey} from './programmes';
it('matches programme labels without merging distinct departments',()=>{
  for(const [a,b] of [
    ['Civil Engineering Technology','Civil Engineering'],
    ['Civil Engineering Full Time ND','Civil Engineering'],
    ['Computer Engineering Technology Part-Time HND','Computer Engineering'],
    ['Mechanical Engineering Technology','Mechanical Engineering'],
    ['Electrical/Electronics Engineering Technology','Electrical and Electronics Engineering'],
    ['Office Technology & Management Full-Time ND','Office Technology and Management'],
    ['Surveying & Geoinformatics','Surveying and Geo-Informatics'],
    ['Accounting','Accountancy'],
  ]) expect(programmeKey(a)).toBe(programmeKey(b));
  expect(programmeKey('Computer Science')).not.toBe(programmeKey('Computer Engineering'));
  expect(programmeKey('Building Technology')).not.toBe(programmeKey('Architectural Technology'));
});
