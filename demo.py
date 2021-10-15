a = [1500]*8

print(a)
import re
a = 12.321321
print(isinstance(a,float))
t = ' Temperature: 24.92 deg C'
t = t.strip()
d = '  Depth: -0.06 m'
d = d.strip()
t_list = re.findall(r'(..\...) deg',t)
d_list = re.findall(r'(.\...) m',d)
r_t=None
r_d=None
if len(t_list)>0:
    r_t = float(t_list[0])
if len(d_list)>0:
    r_d = float(d_list[0])
print('r_t',r_t)
print('r_d',r_d)
