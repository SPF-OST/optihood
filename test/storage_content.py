import pandas as pd
import matplotlib.pyplot as plt
building = 3
storage = 3
temperatures = [35, 50, 65]
type = 'group'
input_path = f'.\Test\TestCase\FeedinMed\cost\{type}'


for l in range(1,building+1):
    for k in range(storage):
        df0 = pd.read_excel(input_path+r'\{}'.format('results_3b_new.xlsx'),
                            sheet_name=f'heatStorageBus{0}__Building{l}')
        df1 = pd.read_excel(input_path+r'\{}'.format('results_3b_new.xlsx'),
                            sheet_name=f'heatStorageBus{1}__Building{l}')
        df2 = pd.read_excel(input_path+r'\{}'.format('results_3b_new.xlsx'),
                            sheet_name=f'heatStorageBus{2}__Building{l}')
        df_hb0 = pd.read_excel(input_path+r'\{}'.format('results_3b_new.xlsx'),
                            sheet_name=f'heatBus{0}__Building{l}')
        df_hb2 = pd.read_excel(input_path+r'\{}'.format('results_3b_new.xlsx'),
                            sheet_name=f'heatBus{2}__Building{l}')
        df=pd.read_excel(input_path+r'\{}'.format('results_3b_new.xlsx'), sheet_name=f'heatStorageBus{k}__Building{l}')
        flow = df[f"(('HP__Building{l}', 'heatStorageBus{k}__Building{l}'), 'flow')"]
        heatbus0= df_hb0[f"(('heatBus0__Building{l}', 'heat0__Building{l}'), 'flow')"]
        heatbus2= df_hb2[f"(('heatBus2__Building{l}', 'heat2__Building{l}'), 'flow')"]
        store = df['storage_content']
        time = (df['Unnamed: 0'])
        time_to_0 = []
        i=0
        j=0
        temp=0

        while i < len(store):
            j = i
            if store[i] != 0:
                temp+=1

                while store[j+1] !=0 and j<(len(store)-2):
                    temp+=1
                    j+=1
                time_to_0.append(temp)
            if temp == 1:
                if k ==0:
                    inflow = store[j] + flow[j + 1]
                    outflow = df1[f"(('HP__Building{l}', 'heatStorageBus{1}__Building{l}'), 'flow')"][j+1] + heatbus0[j+1]
                    if outflow - inflow < 0.05:
                        print("Transfert!")
                        print(j)
                    else:
                        print("NO TRASNFERT!")
                        print(k, j, store[j])
                elif k == 1:
                    inflow = store[j] + flow[j+1]
                    if inflow - df2[f"(('HP__Building{l}', 'heatStorageBus{2}__Building{l}'), 'flow')"][j+1] <0.02:
                        print("transfert!")
                        print(j)
                    else:
                        print("NO TRANSFERT!")
                        print(j)
                elif k == 3:
                    inflow = store[j] + flow[j + 1]
                    outflow = heatbus2[j + 1]
                    if outflow - inflow < 0.05:
                        print("Transfert!")
                        print(j)
                    else:
                        print("NO TRASNFERT!")
                        print(k, j, store[j])
            temp = 0

            i=j+1

        plt.plot(time, store)
        plt.title(f'Storage{temperatures[k]} building {l}')
        plt.xlabel('Time')
        plt.ylabel('Storage content')
        plt.show()
        plt.hist(time_to_0, bins=50)
        plt.title(f'Time to 0 Storage{temperatures[k]} building {l}')
        plt.xlabel('time to 0')
        plt.ylabel('Counts')
        plt.show()

